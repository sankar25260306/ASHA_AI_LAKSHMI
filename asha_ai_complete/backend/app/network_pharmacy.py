"""ASHA AI demo network + pharmacy module. All seeded branch/stock records are fictional.
Production deployment requires verified hospital authorization, secret management, HTTPS,
security testing, clinical/privacy review, and replacement of demo seed data.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sqlite3, os, secrets, hashlib, hmac, base64, json, csv
from .multi_agent import ANALYSIS_TYPES, analyze_network_snapshot, llm_runtime_status

router = APIRouter(prefix="/api/network", tags=["Lakshmi Hospital Network (DEMO)"])
DB = Path(__file__).resolve().parent.parent / "data" / "asha_network_pharmacy.sqlite"
DB.parent.mkdir(parents=True, exist_ok=True)
TOKEN_SECRET = os.environ.get("ASHA_TOKEN_SECRET", "DEMO_ONLY_CHANGE_THIS_SECRET_BEFORE_DEPLOYMENT").encode()
NETWORK_NAME = "Lakshmi Hospital Network (DEMO — branch affiliations unverified)"
DISTRICTS = ["Ariyalur","Chengalpattu","Chennai","Coimbatore","Cuddalore","Dharmapuri","Dindigul","Erode","Kallakurichi","Kancheepuram","Kanniyakumari","Karur","Krishnagiri","Madurai","Mayiladuthurai","Nagapattinam","Namakkal","Nilgiris","Perambalur","Pudukkottai","Ramanathapuram","Ranipet","Salem","Sivaganga","Tenkasi","Thanjavur","Theni","Thoothukudi","Tiruchirappalli","Tirunelveli","Tirupathur","Tiruppur","Tiruvallur","Tiruvannamalai","Tiruvarur","Vellore","Viluppuram","Virudhunagar"]
MEDICINES = [
 ("MED-PAR-500","Paracetamol 500 mg","tablet","OTC_DEMO",120,"2027-06-30"),
 ("MED-CET-10","Cetirizine 10 mg","tablet","OTC_DEMO",80,"2027-04-30"),
 ("MED-ORS-01","ORS sachet","sachet","OTC_DEMO",60,"2027-03-31"),
 ("MED-PAN-40","Pantoprazole 40 mg","tablet","PRESCRIPTION_DEMO",45,"2027-02-28"),
 ("MED-AMX-500","Amoxicillin 500 mg","capsule","PRESCRIPTION_DEMO",30,"2027-01-31"),
 ("MED-INS-01","Insulin (cold-chain item)","vial","PRESCRIPTION_COLD_CHAIN_DEMO",12,"2026-12-31"),
]
ROLES = {"super_admin", "network_admin", "hospital_admin", "doctor", "dispatcher", "driver", "pharmacy_staff", "auditor"}

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def now(): return datetime.now(timezone.utc).isoformat()

def hash_password(password, salt=None):
 salt=salt or secrets.token_bytes(16); dk=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
 return base64.b64encode(salt).decode()+":"+base64.b64encode(dk).decode()

def check_password(password, stored):
 try:
  salt_b, hash_b=stored.split(":",1); salt=base64.b64decode(salt_b); expected=base64.b64decode(hash_b)
  actual=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
  return hmac.compare_digest(actual,expected)
 except Exception: return False

def init_db():
 c=db(); q=c.cursor()
 q.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, organization TEXT NOT NULL, branch_id TEXT, active INTEGER NOT NULL DEFAULT 1, must_change_password INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS branches(branch_id TEXT PRIMARY KEY, network_name TEXT NOT NULL, district TEXT NOT NULL, display_name TEXT NOT NULL, address TEXT, phone TEXT, latitude REAL, longitude REAL, verification_status TEXT NOT NULL, data_source TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS pharmacy_stock(id INTEGER PRIMARY KEY AUTOINCREMENT, branch_id TEXT NOT NULL, medicine_code TEXT NOT NULL, medicine_name TEXT NOT NULL, dosage TEXT NOT NULL, form TEXT NOT NULL, stock_quantity INTEGER NOT NULL, reserved_quantity INTEGER NOT NULL DEFAULT 0, reorder_level INTEGER NOT NULL, expiry_date TEXT NOT NULL, prescription_type TEXT NOT NULL, storage_note TEXT, verification_status TEXT NOT NULL, updated_at TEXT NOT NULL, updated_by TEXT, FOREIGN KEY(branch_id) REFERENCES branches(branch_id));
 CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, action TEXT NOT NULL, resource TEXT NOT NULL, record_id TEXT, details TEXT, created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS app_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
 """)
 # Demo credentials; force password change after first login.
 if not q.execute("SELECT 1 FROM users WHERE username='superadmin'").fetchone():
  pwd=os.environ.get('ASHA_BOOTSTRAP_PASSWORD','ASHA-Demo-2026!')
  q.execute('INSERT INTO users(username,password_hash,role,organization,branch_id,active,must_change_password,created_at) VALUES(?,?,?,?,?,?,?,?)',('superadmin',hash_password(pwd),'super_admin',NETWORK_NAME,None,1,1,now()))
 # Branches are district placeholders, not proof of actual franchises.
 for i,d in enumerate(DISTRICTS,1):
  bid=f'LHN-TN-{i:02d}'
  q.execute('INSERT OR IGNORE INTO branches VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(bid,NETWORK_NAME,d,f'Lakshmi Hospital — {d} District (DEMO PLACEHOLDER)',None,None,None,None,'DEMO_UNVERIFIED','SYNTHETIC_SEED',1,now()))

 # One-time, versioned import. Prefer the explicitly requested 1,000-row pharmacy file.
 # If this package is run over an earlier demo database, only rows created by the old
 # synthetic seed are replaced; records entered by named users are retained.
 pharmacy_csv=Path(__file__).resolve().parent.parent/'data'/'asha_lakshmi_pharmacy_1000_demo.csv'
 legacy_csv=Path(__file__).resolve().parent.parent/'data'/'lakshmi_pharmacy_inventory_10000_demo.csv'
 target_version='pharmacy_1000_v1' if pharmacy_csv.exists() else 'pharmacy_10000_legacy_v1'
 prior=q.execute("SELECT value FROM app_metadata WHERE key='pharmacy_seed_version'").fetchone()
 if not prior or prior['value'] != target_version:
  q.execute("DELETE FROM pharmacy_stock WHERE updated_by IN ('seed','synthetic_seed','synthetic_seed_1000')")
  branch_by_district={row['district']:row['branch_id'] for row in q.execute('SELECT branch_id,district FROM branches')}
  if pharmacy_csv.exists():
   imported=0
   with pharmacy_csv.open('r',encoding='utf-8-sig',newline='') as fh:
    for row in csv.DictReader(fh):
     district=(row.get('district') or '').strip()
     # Normalize common spelling variant in district CSVs.
     district_aliases={'Villupuram':'Viluppuram'}
     district=district_aliases.get(district,district)
     bid=branch_by_district.get(district)
     if not bid:
      continue
     qty=max(0,int(float(row.get('stock_quantity') or 0)))
     reserved=min(qty,max(0,int(float(row.get('reserved_quantity') or 0))))
     reorder=max(0,int(float(row.get('reorder_level') or 0)))
     expiry=row.get('expiry_date') or '2027-12-31'
     try: datetime.strptime(expiry,'%Y-%m-%d')
     except ValueError: expiry='2027-12-31'
     code=(row.get('record_id') or f'PHARM-DEMO-{imported+1:04d}').strip()
     q.execute('INSERT INTO pharmacy_stock(branch_id,medicine_code,medicine_name,dosage,form,stock_quantity,reserved_quantity,reorder_level,expiry_date,prescription_type,storage_note,verification_status,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      (bid,code,(row.get('medicine_name') or 'Demo medicine').strip(),(row.get('strength') or 'Demo spec').strip(),(row.get('dosage_form') or 'other').strip(),qty,reserved,reorder,expiry,'SYNTHETIC_DEMO','Synthetic data; verify all fields before use','DEMO_UNVERIFIED',now(),'synthetic_seed_1000'))
     imported += 1
   if imported != 1000:
    raise RuntimeError(f'Expected 1,000 pharmacy demo rows but imported {imported}. Check the CSV format.')
  else:
   for i,d in enumerate(DISTRICTS,1):
    bid=f'LHN-TN-{i:02d}'
    for m in MEDICINES:
     code,name,form,ptype,qty,expiry=m
     q.execute('INSERT INTO pharmacy_stock(branch_id,medicine_code,medicine_name,dosage,form,stock_quantity,reserved_quantity,reorder_level,expiry_date,prescription_type,storage_note,verification_status,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(bid,code,name,name,form,qty,0,max(10,qty//4),expiry,ptype,'Demo only; verify storage and cold-chain requirements','DEMO_UNVERIFIED',now(),'seed'))
   if legacy_csv.exists():
    imported=0
    with legacy_csv.open('r',encoding='utf-8-sig',newline='') as fh:
     for row in csv.DictReader(fh):
      bid=row.get('branch_id','')
      if not q.execute('SELECT 1 FROM branches WHERE branch_id=?',(bid,)).fetchone():
       continue
      qty=max(0,int(float(row.get('quantity_demo') or 0))); reserved=min(qty,max(0,int(float(row.get('reserved_quantity_demo') or 0))))
      q.execute('INSERT INTO pharmacy_stock(branch_id,medicine_code,medicine_name,dosage,form,stock_quantity,reserved_quantity,reorder_level,expiry_date,prescription_type,storage_note,verification_status,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
       (bid,row.get('stock_id') or f'LHN-DEMO-{imported+1:05d}',row.get('medicine_name','Demo medicine'),row.get('dosage_or_spec','demo'),row.get('form','demo'),qty,reserved,max(0,int(float(row.get('reorder_level_demo') or 25))),row.get('expiry_date_demo','2027-12-31'),row.get('prescription_type_demo','DEMO_ONLY'),'Synthetic demo inventory; verify before use','DEMO_UNVERIFIED',now(),'synthetic_seed'))
      imported += 1
      if imported>=max(0,10000-q.execute('SELECT COUNT(*) FROM pharmacy_stock').fetchone()[0]): break
  q.execute("INSERT INTO app_metadata(key,value) VALUES('pharmacy_seed_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(target_version,))
 c.commit(); c.close()

init_db()

def audit(user, action, resource, record_id=None, details=None):
 c=db(); c.execute('INSERT INTO audit_logs(username,role,action,resource,record_id,details,created_at) VALUES(?,?,?,?,?,?,?)',(user.get('username') if user else 'anonymous',user.get('role') if user else 'anonymous',action,resource,str(record_id) if record_id is not None else None,json.dumps(details or {},ensure_ascii=False),now())); c.commit(); c.close()

def token_for(username):
 expiry=int((datetime.now(timezone.utc)+timedelta(hours=8)).timestamp()); raw=f'{username}|{expiry}'; sig=hmac.new(TOKEN_SECRET,raw.encode(),hashlib.sha256).hexdigest(); return base64.urlsafe_b64encode(f'{raw}|{sig}'.encode()).decode().rstrip('='), expiry

def current_user(authorization: Optional[str] = Header(None)):
 if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'Login required')
 try:
  token=authorization.split(' ',1)[1]; payload=base64.urlsafe_b64decode(token+'='*(-len(token)%4)).decode(); username,exp,sig=payload.rsplit('|',2); raw=f'{username}|{exp}'
  if not hmac.compare_digest(sig,hmac.new(TOKEN_SECRET,raw.encode(),hashlib.sha256).hexdigest()) or int(exp)<int(datetime.now(timezone.utc).timestamp()): raise ValueError()
 except Exception: raise HTTPException(401,'Invalid or expired session')
 c=db(); sess=c.execute('SELECT 1 FROM sessions WHERE token_hash=? AND username=? AND expires_at>?',(hashlib.sha256(token.encode()).hexdigest(),username,now())).fetchone()
 if not sess: c.close(); raise HTTPException(401,'Session revoked or expired')
 row=c.execute('SELECT username,role,organization,branch_id,active,must_change_password FROM users WHERE username=?',(username,)).fetchone(); c.close()
 if not row or not row['active']: raise HTTPException(401,'Account disabled')
 return dict(row)

def roles(*allowed):
 def dep(user=Depends(current_user)):
  if user['role'] not in allowed: raise HTTPException(403,'Insufficient permission')
  return user
 return dep

def scope_branch(user, branch_id):
 if user['role']=='super_admin' or user['role']=='network_admin': return
 if user.get('branch_id') != branch_id: raise HTTPException(403,'This account can access only its assigned branch')

class LoginIn(BaseModel): role:str=Field(min_length=1,max_length=40); username:str=Field(min_length=3,max_length=120); password:str=Field(min_length=1,max_length=128)
class ChangePasswordIn(BaseModel): current_password:str; new_password:str=Field(min_length=12,max_length=128)
class BranchIn(BaseModel): district:str; display_name:str=Field(min_length=3,max_length=150); address:Optional[str]=None; phone:Optional[str]=None; latitude:Optional[float]=Field(default=None,ge=-90,le=90); longitude:Optional[float]=Field(default=None,ge=-180,le=180); verification_status:str='DEMO_UNVERIFIED'
class StockIn(BaseModel): branch_id:str; medicine_code:str=Field(min_length=2,max_length=40); medicine_name:str=Field(min_length=2,max_length=150); dosage:str=Field(min_length=1,max_length=80); form:str=Field(min_length=2,max_length=40); stock_quantity:int=Field(ge=0,le=1000000); reserved_quantity:int=Field(default=0,ge=0,le=1000000); reorder_level:int=Field(default=10,ge=0,le=1000000); expiry_date:str; prescription_type:str='VERIFY_WITH_PHARMACIST'; storage_note:Optional[str]=None; verification_status:str='UNVERIFIED'
class StockUpdate(BaseModel): stock_quantity:int=Field(ge=0,le=1000000); reserved_quantity:int=Field(ge=0,le=1000000); reorder_level:int=Field(ge=0,le=1000000); expiry_date:str; verification_status:str='UNVERIFIED'
class AgentAnalysisIn(BaseModel): analysis_type:str=Field(default='network_readiness',min_length=3,max_length=50); district:Optional[str]=Field(default=None,min_length=2,max_length=80)

@router.post('/auth/login')
def login(x:LoginIn):
 c=db(); u=c.execute('SELECT * FROM users WHERE username=?',(x.username,)).fetchone()
 if not u or not u['active'] or not check_password(x.password,u['password_hash']) or x.role not in ROLES or x.role != u['role']:
  audit(None,'LOGIN_FAILED','user',x.username,{'selected_role':x.role}); c.close(); raise HTTPException(401,'Invalid username, password, or selected role')
 tok,expiry=token_for(x.username); th=hashlib.sha256(tok.encode()).hexdigest(); c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(th,x.username,datetime.fromtimestamp(expiry,timezone.utc).isoformat())); c.commit(); result={k:u[k] for k in ['username','role','organization','branch_id','must_change_password']}; c.close(); audit(result,'LOGIN_SUCCESS','session',x.username); return {'access_token':tok,'token_type':'bearer','expires_at':expiry,'user':result,'demo_warning':'Prototype account. Change bootstrap password before any shared/network use.'}

@router.post('/auth/logout')
def logout(authorization: Optional[str] = Header(None), user=Depends(current_user)):
 token=authorization.split(' ',1)[1]; c=db(); c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)); c.commit(); c.close(); audit(user,'LOGOUT','session',user['username']); return {'ok':True,'message':'Session revoked'}

@router.post('/auth/change-password')
def change_password(x:ChangePasswordIn,user=Depends(current_user)):
 c=db(); row=c.execute('SELECT password_hash FROM users WHERE username=?',(user['username'],)).fetchone()
 if not row or not check_password(x.current_password,row['password_hash']): c.close(); raise HTTPException(400,'Current password is incorrect')
 c.execute('UPDATE users SET password_hash=?,must_change_password=0 WHERE username=?',(hash_password(x.new_password),user['username'])); c.commit(); c.close(); audit(user,'PASSWORD_CHANGED','user',user['username']); return {'ok':True,'message':'Password updated'}

@router.get('/me')
def me(user=Depends(current_user)): return {'user':user,'network':NETWORK_NAME,'data_type':'DEMO_UNVERIFIED'}

@router.post('/users', status_code=201)
def create_user(x:dict, user=Depends(roles('super_admin'))):
 username=str(x.get('username','')).strip(); password=str(x.get('temporary_password','')); role=x.get('role'); org=str(x.get('organization') or NETWORK_NAME); branch=x.get('branch_id')
 if len(username)<3 or len(password)<12 or role not in ROLES: raise HTTPException(422,'username >=3 chars, temporary_password >=12 chars and a valid role are required')
 if role in {'hospital_admin','doctor','dispatcher','driver','pharmacy_staff'} and not branch: raise HTTPException(422,'A branch_id is required for branch-scoped roles')
 c=db()
 if branch and not c.execute('SELECT 1 FROM branches WHERE branch_id=?',(branch,)).fetchone(): c.close(); raise HTTPException(404,'Branch not found')
 try: c.execute('INSERT INTO users(username,password_hash,role,organization,branch_id,active,must_change_password,created_at) VALUES(?,?,?,?,?,?,?,?)',(username,hash_password(password),role,org,branch,1,1,now())); c.commit()
 except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'Username already exists')
 c.close(); audit(user,'USER_CREATED','user',username,{'role':role,'branch_id':branch}); return {'created':True,'username':username,'role':role,'must_change_password':True}

@router.get('/users')
def list_users(user=Depends(roles('super_admin'))):
 c=db(); rows=[dict(r) for r in c.execute('SELECT id,username,role,organization,branch_id,active,must_change_password,created_at FROM users ORDER BY id')]; c.close(); audit(user,'USER_LIST_VIEWED','users'); return {'items':rows,'count':len(rows)}

@router.patch('/users/{username}/active')
def set_user_active(username:str, active:bool, user=Depends(roles('super_admin'))):
 if username==user['username'] and not active: raise HTTPException(400,'Cannot disable your own active session account')
 c=db(); cur=c.execute('UPDATE users SET active=? WHERE username=?',(int(active),username)); c.commit(); c.close()
 if cur.rowcount==0: raise HTTPException(404,'User not found')
 audit(user,'USER_ACTIVE_CHANGED','user',username,{'active':active}); return {'ok':True,'username':username,'active':active}

@router.get('/branches')
def branches(district:Optional[str]=None, user=Depends(current_user)):
 c=db(); sql='SELECT * FROM branches'; args=[]; conditions=[]
 if district:
  conditions.append('district=?'); args.append(district)
 if user['role'] not in {'super_admin','network_admin','auditor'} and user.get('branch_id'):
  conditions.append('branch_id=?'); args.append(user['branch_id'])
 if conditions: sql += ' WHERE ' + ' AND '.join(conditions)
 sql+=' ORDER BY district'; rows=[dict(r) for r in c.execute(sql,args)]; c.close(); return {'network':NETWORK_NAME,'districts_included':len(DISTRICTS),'items':rows,'count':len(rows),'data_type':'DEMO_UNVERIFIED','notice':'These are district placeholders, not verified Lakshmi Hospital branches.'}

@router.post('/branches',status_code=201)
def create_branch(x:BranchIn,user=Depends(roles('super_admin','network_admin'))):
 if x.district not in DISTRICTS: raise HTTPException(422,'Select one of the 38 Tamil Nadu districts')
 if 'lakshmi hospital' not in x.display_name.casefold(): raise HTTPException(422,'This network accepts Lakshmi Hospital branches only. Verify the franchise affiliation before adding a real branch.')
 bid='LHN-'+secrets.token_hex(4).upper(); c=db(); c.execute('INSERT INTO branches VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(bid,NETWORK_NAME,x.district,x.display_name,x.address,x.phone,x.latitude,x.longitude,x.verification_status,'ADMIN_ENTERED',1,now())); c.commit(); c.close(); audit(user,'BRANCH_CREATED','branch',bid,{'district':x.district,'verification_status':x.verification_status}); return {'branch_id':bid,'created':True,'verification_status':x.verification_status}

@router.patch('/branches/{branch_id}/verification')
def verify_branch(branch_id:str,status:str,user=Depends(roles('super_admin','network_admin'))):
 if status not in {'DEMO_UNVERIFIED','PENDING_DOCUMENTS','VERIFIED_BY_AUTHORIZED_ADMIN','INACTIVE'}: raise HTTPException(422,'Unsupported verification status')
 c=db(); cur=c.execute('UPDATE branches SET verification_status=?,updated_at=? WHERE branch_id=?',(status,now(),branch_id)); c.commit(); c.close()
 if cur.rowcount==0: raise HTTPException(404,'Branch not found')
 audit(user,'BRANCH_VERIFICATION_CHANGED','branch',branch_id,{'status':status}); return {'ok':True,'branch_id':branch_id,'verification_status':status}

@router.get('/pharmacy/stock')
def pharmacy_stock(branch_id:Optional[str]=None, search:Optional[str]=None, alerts_only:bool=False, limit:int=500, user=Depends(current_user)):
 if limit<1 or limit>1000: raise HTTPException(422,'limit must be 1..1000')
 c=db(); sql='SELECT p.*,b.district,b.display_name FROM pharmacy_stock p JOIN branches b ON p.branch_id=b.branch_id WHERE 1=1'; args=[]
 if user['role'] not in {'super_admin','network_admin','auditor'} and user.get('branch_id'): sql+=' AND p.branch_id=?'; args.append(user['branch_id'])
 elif branch_id: sql+=' AND p.branch_id=?'; args.append(branch_id)
 if search: sql+=' AND (p.medicine_name LIKE ? OR p.medicine_code LIKE ?)'; args += [f'%{search}%',f'%{search}%']
 if alerts_only: sql+=' AND (p.stock_quantity-p.reserved_quantity<=p.reorder_level OR date(p.expiry_date)<=date(\'now\',\'+90 day\'))'
 sql+=' ORDER BY b.district,p.medicine_name LIMIT ?'; args.append(limit); rows=[dict(r) for r in c.execute(sql,args)]; c.close()
 for r in rows: r['available_quantity']=max(0,r['stock_quantity']-r['reserved_quantity']); r['low_stock']=(r['stock_quantity']-r['reserved_quantity']<=r['reorder_level']); r['expiry_alert']=r['expiry_date']<= (datetime.now(timezone.utc)+timedelta(days=90)).date().isoformat()
 return {'items':rows,'count':len(rows),'data_type':'DEMO_UNVERIFIED','notice':'Stock quantities are synthetic placeholders. Never dispense medicine based on this demo inventory.'}

@router.post('/pharmacy/stock',status_code=201)
def add_stock(x:StockIn,user=Depends(roles('super_admin','network_admin','hospital_admin','pharmacy_staff'))):
 scope_branch(user,x.branch_id)
 if x.reserved_quantity > x.stock_quantity: raise HTTPException(422,'reserved_quantity cannot exceed stock_quantity')
 try: datetime.strptime(x.expiry_date,'%Y-%m-%d')
 except ValueError: raise HTTPException(422,'expiry_date must use YYYY-MM-DD')
 c=db();
 if not c.execute('SELECT 1 FROM branches WHERE branch_id=?',(x.branch_id,)).fetchone(): c.close(); raise HTTPException(404,'Branch not found')
 cur=c.execute('INSERT INTO pharmacy_stock(branch_id,medicine_code,medicine_name,dosage,form,stock_quantity,reserved_quantity,reorder_level,expiry_date,prescription_type,storage_note,verification_status,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(x.branch_id,x.medicine_code,x.medicine_name,x.dosage,x.form,x.stock_quantity,x.reserved_quantity,x.reorder_level,x.expiry_date,x.prescription_type,x.storage_note,x.verification_status,now(),user['username'])); c.commit(); item=cur.lastrowid; c.close(); audit(user,'PHARMACY_STOCK_CREATED','pharmacy_stock',item,{'branch_id':x.branch_id,'medicine_code':x.medicine_code}); return {'created':True,'id':item,'data_type':x.verification_status}

@router.put('/pharmacy/stock/{stock_id}')
def update_stock(stock_id:int,x:StockUpdate,user=Depends(roles('super_admin','network_admin','hospital_admin','pharmacy_staff'))):
 if x.reserved_quantity > x.stock_quantity: raise HTTPException(422,'reserved_quantity cannot exceed stock_quantity')
 try: datetime.strptime(x.expiry_date,'%Y-%m-%d')
 except ValueError: raise HTTPException(422,'expiry_date must use YYYY-MM-DD')
 c=db(); row=c.execute('SELECT branch_id FROM pharmacy_stock WHERE id=?',(stock_id,)).fetchone()
 if not row: c.close(); raise HTTPException(404,'Stock record not found')
 scope_branch(user,row['branch_id']); c.execute('UPDATE pharmacy_stock SET stock_quantity=?,reserved_quantity=?,reorder_level=?,expiry_date=?,verification_status=?,updated_at=?,updated_by=? WHERE id=?',(x.stock_quantity,x.reserved_quantity,x.reorder_level,x.expiry_date,x.verification_status,now(),user['username'],stock_id)); c.commit(); c.close(); audit(user,'PHARMACY_STOCK_UPDATED','pharmacy_stock',stock_id,x.model_dump()); return {'ok':True,'id':stock_id}

@router.get('/pharmacy/summary')
def pharmacy_summary(user=Depends(current_user)):
 c=db()
 sql='SELECT p.*,b.district FROM pharmacy_stock p JOIN branches b ON p.branch_id=b.branch_id WHERE 1=1'
 args=[]
 if user['role'] not in {'super_admin','network_admin','auditor'} and user.get('branch_id'):
  sql+=' AND p.branch_id=?'; args.append(user['branch_id'])
 rows=[dict(r) for r in c.execute(sql,args)]
 c.close()
 today=datetime.now(timezone.utc).date()
 return {'data_type':'DEMO_UNVERIFIED','medicine_records':len(rows),'total_available_units':sum(max(0,x['stock_quantity']-x['reserved_quantity']) for x in rows),'low_stock_records':sum((x['stock_quantity']-x['reserved_quantity'])<=x['reorder_level'] for x in rows),'expiry_alert_records':sum(x['expiry_date'] <= (today+timedelta(days=90)).isoformat() for x in rows),'branches_covered':len(set(x['branch_id'] for x in rows)),'notice':'Demo summary only; all quantities are synthetic and must not be used for dispensing.'}


@router.get('/audit-logs')
def audit_logs(limit:int=200,user=Depends(roles('super_admin','auditor'))):
 if limit<1 or limit>1000: raise HTTPException(422,'limit must be 1..1000')
 c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?',(limit,))]; c.close(); return {'items':rows,'count':len(rows),'read_only':True}

@router.get('/overview')
def overview(user=Depends(current_user)):
 c=db(); branches_n=c.execute('SELECT count(*) FROM branches WHERE active=1').fetchone()[0]; meds=c.execute('SELECT count(*) FROM pharmacy_stock').fetchone()[0]; users=c.execute('SELECT count(*) FROM users WHERE active=1').fetchone()[0]; low=c.execute('SELECT count(*) FROM pharmacy_stock WHERE stock_quantity-reserved_quantity<=reorder_level').fetchone()[0]; c.close()
 return {'network':NETWORK_NAME,'district_placeholders':branches_n,'pharmacy_records':meds,'active_users':users if user['role']=='super_admin' else None,'low_stock_demo_records':low,'data_type':'DEMO_UNVERIFIED','roles':sorted(ROLES),'security_notice':'Demo-only seed data. Configure ASHA_TOKEN_SECRET and ASHA_BOOTSTRAP_PASSWORD before shared deployment.'}


# --------------------------------------------------
# MULTI-AGENT LLM LOGISTICS EXPLANATION (DEMO ONLY)
# --------------------------------------------------

@router.get('/agents/status')
def multi_agent_status(user=Depends(current_user)):
    """Report configured LLM state without exposing credentials."""
    llm = llm_runtime_status()
    return {
        'multi_agent_enabled': True,
        'agents': [
            'Hospital Resource Agent',
            'Ambulance Operations Agent',
            'Pharmacy Inventory Agent',
            'Self-Doubt / Verification Agent',
            'LLM Orchestrator / Explanation Layer',
        ],
        'analysis_types': ANALYSIS_TYPES,
        'llm': llm,
        'data_type': 'SYNTHETIC_DEMO_NOT_REAL',
        'notice': 'Agent outputs are logistical demo summaries only. No diagnosis, prescription, dispatch, or stock ordering.',
    }


@router.post('/agents/analyze')
def multi_agent_analyze(x: AgentAnalysisIn, user=Depends(roles('super_admin','network_admin','hospital_admin','doctor','dispatcher','driver','pharmacy_staff'))):
    if x.analysis_type not in ANALYSIS_TYPES:
        raise HTTPException(422, 'Unsupported analysis_type. Choose one of: ' + ', '.join(sorted(ANALYSIS_TYPES)))
    district = x.district.strip() if x.district else None
    if district:
        matched_district = next((item for item in DISTRICTS if item.casefold() == district.casefold()), None)
        if not matched_district:
            raise HTTPException(422, 'Select a district from the Tamil Nadu demo list.')
        district = matched_district

    # Branch-scoped accounts can only run the analysis for their assigned branch.
    branch_scope = None
    if user['role'] not in {'super_admin', 'network_admin'}:
        branch_scope = user.get('branch_id')
        if not branch_scope:
            raise HTTPException(403, 'This account must be assigned to a verified/approved branch scope by the Super Admin.')
        c = db()
        b = c.execute('SELECT district FROM branches WHERE branch_id=? AND active=1', (branch_scope,)).fetchone()
        c.close()
        if not b:
            raise HTTPException(403, 'Assigned branch is unavailable.')
        assigned_district = b['district']
        if district and district.casefold() != assigned_district.casefold():
            raise HTTPException(403, 'This account can analyze only its assigned branch/district.')
        district = assigned_district

    try:
        result = analyze_network_snapshot(x.analysis_type, district, branch_scope)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    audit(user, 'MULTI_AGENT_ANALYSIS', 'multi_agent', x.analysis_type, {
        'district': district,
        'explanation_source': result.get('explanation_source'),
        'llm_provider': (result.get('llm') or {}).get('provider'),
        'llm_used': (result.get('llm') or {}).get('used', False),
    })
    result['requested_by_role'] = user['role']
    return result


# --------------------------------------------------
# BOUNDED AUTONOMOUS MONITORING (DEMO ONLY)
# --------------------------------------------------

class AutonomousSettingsIn(BaseModel):
    enabled: bool
    interval_seconds: int = Field(default=300, ge=60, le=3600)


@router.get('/autonomous/status')
def autonomous_status(user=Depends(current_user)):
    from .autonomous import get_status
    return get_status()


@router.get('/autonomous/runs')
def autonomous_runs(limit: int = 20, user=Depends(current_user)):
    from .autonomous import list_runs
    items = list_runs(limit)
    return {"items": items, "count": len(items), "data_type": "SYNTHETIC_DEMO_NOT_REAL", "human_review_required": True}


@router.post('/autonomous/run')
def autonomous_run_now(user=Depends(roles('super_admin', 'network_admin'))):
    from .autonomous import run_autonomous_cycle
    result = run_autonomous_cycle(user['username'])
    audit(user, 'AUTONOMOUS_MONITOR_RUN', 'autonomous_monitor', result.get('id'), {
        'status': result.get('status'), 'alert_count': result.get('alert_count'), 'data_type': result.get('data_type')
    })
    return result


@router.patch('/autonomous/settings')
def autonomous_update_settings(x: AutonomousSettingsIn, user=Depends(roles('super_admin'))):
    from .autonomous import update_settings
    try:
        settings = update_settings(x.enabled, x.interval_seconds, user['username'])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    audit(user, 'AUTONOMOUS_SETTINGS_CHANGED', 'autonomous_monitor', 'singleton', settings)
    return {**settings, 'mode': 'bounded_autonomy', 'human_review_required': True,
            'notice': 'This setting controls scheduled demo monitoring only. It never authorizes dispatch, clinical decisions, medicine orders, or stock changes.'}
