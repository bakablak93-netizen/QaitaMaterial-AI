from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import Base, engine, db_session
from app.models import Company, User, Material, Request, ChatMessage
from app.schemas import Register, Login, MaterialIn, MaterialOut, RequestIn, MessageIn, EconomyIn
from app.core.security import hash_password, verify_password, issue_token, token_uid
from app.core.config import settings
from app.services.analysis import analyze, economy
from app.services.llm_service import configured, chat

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine) # Development bootstrap only; production should use migrations.
    yield

app=FastAPI(title="QaitaMaterial AI API",version="0.1.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings().cors_origins.split(",")],allow_credentials=True,allow_methods=["GET","POST","PATCH","DELETE"],allow_headers=["Authorization","Content-Type"])

def current_user(authorization: str | None=Header(default=None),db: Session=Depends(db_session)):
    token=(authorization or "").removeprefix("Bearer ")
    uid=token_uid(token)
    user=db.get(User,uid) if uid is not None else None
    if not user: raise HTTPException(401,"Authentication required")
    return user

def owner_or_admin(material,user):
    if material.company_id != user.company_id and user.role != "admin":raise HTTPException(403,"Access denied")

@app.get('/api/health')
def health():return {"status":"ok","version":"0.1.0"}

@app.post('/api/auth/register')
def register(payload: Register,db:Session=Depends(db_session)):
    if payload.role not in ("factory","buyer"):raise HTTPException(422,"Invalid role")
    if db.scalar(select(User).where(User.email==payload.email)):raise HTTPException(409,"Email already used")
    company=db.scalar(select(Company).where(Company.name==payload.company_name))
    if company:raise HTTPException(409,"Company name already exists; contact its administrator")
    company=Company(name=payload.company_name)
    db.add(company);db.flush()
    user=User(name=payload.name,email=payload.email,password_hash=hash_password(payload.password),role=payload.role,company_id=company.id)
    db.add(user);db.commit();db.refresh(user)
    return {"access_token":issue_token(user.id),"token_type":"bearer","user":{"id":user.id,"name":user.name,"role":user.role,"company_id":user.company_id}}

@app.post('/api/auth/login')
def login(payload:Login,db:Session=Depends(db_session)):
    user=db.scalar(select(User).where(User.email==payload.email.strip().lower()))
    if not user or not verify_password(payload.password,user.password_hash):raise HTTPException(401,"Invalid credentials")
    return {"access_token":issue_token(user.id),"token_type":"bearer","user":{"id":user.id,"name":user.name,"role":user.role,"company_id":user.company_id}}

@app.get('/api/me')
def me(user:User=Depends(current_user)):
    return {"id":user.id,"name":user.name,"email":user.email,"role":user.role,"company_id":user.company_id}

@app.get('/api/companies')
def companies(db:Session=Depends(db_session),user:User=Depends(current_user)):
    return [{"id":c.id,"name":c.name,"industry":c.industry,"city":c.city,"is_demo":c.is_demo} for c in db.scalars(select(Company).order_by(Company.name)).all()]

@app.get('/api/materials',response_model=list[MaterialOut])
def materials(search:str='',category:str='',limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),db:Session=Depends(db_session),user:User=Depends(current_user)):
    query=select(Material)
    if search:query=query.where(Material.name.ilike(f'%{search}%'))
    if category:query=query.where(Material.category==category)
    return db.scalars(query.order_by(Material.id.desc()).offset(offset).limit(limit)).all()

@app.post('/api/materials',response_model=MaterialOut,status_code=201)
def add_material(payload:MaterialIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role not in ("factory","admin"):raise HTTPException(403,"Only suppliers can create materials")
    item=Material(**payload.model_dump(),company_id=user.company_id)
    db.add(item);db.commit();db.refresh(item);return item

@app.get('/api/materials/{mid}',response_model=MaterialOut)
def material_detail(mid:int,db:Session=Depends(db_session),user:User=Depends(current_user)):
    item=db.get(Material,mid)
    if not item:raise HTTPException(404,"Material not found")
    return item

@app.patch('/api/materials/{mid}',response_model=MaterialOut)
def change_material(mid:int,payload:MaterialIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    item=db.get(Material,mid)
    if not item:raise HTTPException(404,"Material not found")
    owner_or_admin(item,user)
    for k,v in payload.model_dump().items():setattr(item,k,v)
    db.commit();db.refresh(item);return item

@app.delete('/api/materials/{mid}')
def delete_material(mid:int,db:Session=Depends(db_session),user:User=Depends(current_user)):
    item=db.get(Material,mid)
    if not item:raise HTTPException(404,"Material not found")
    owner_or_admin(item,user)
    if db.scalar(select(Request.id).where(Request.material_id==mid).limit(1)):raise HTTPException(409,"Material has related requests; deletion blocked")
    db.delete(item);db.commit();return {"deleted":True}

@app.get('/api/materials/{mid}/analysis')
def analysis(mid:int,db:Session=Depends(db_session),user:User=Depends(current_user)):
    item=db.get(Material,mid)
    if not item:raise HTTPException(404,"Material not found")
    return analyze(item)

@app.post('/api/economy')
def calculate(payload:EconomyIn,user:User=Depends(current_user)):
    return economy(payload)

@app.get('/api/dashboard')
def dashboard(db:Session=Depends(db_session),user:User=Depends(current_user)):
    rows=db.scalars(select(Material)).all()
    count=db.scalar(select(func.count(Request.id))) or 0
    categories={}
    for row in rows:categories[row.category]=categories.get(row.category,0)+row.quantity*(0.001 if row.unit=="kg" else 1)
    return {"material_count":len(rows),"total_quantity_t":sum(x.quantity*(0.001 if x.unit=='kg' else 1) for x in rows),"request_count":count,"category_quantities":categories,"demo_records":sum(x.is_demo for x in rows),"note":"Includes explicitly marked demo records if seeded; totals are not verified industrial metrics."}

@app.post('/api/requests',status_code=201)
def create_request(payload:RequestIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    item=db.get(Material,payload.material_id)
    if not item:raise HTTPException(404,"Material not found")
    if item.company_id==user.company_id:raise HTTPException(400,"Cannot request own material")
    if payload.requested_quantity>item.quantity:raise HTTPException(422,"Requested quantity exceeds available quantity")
    req=Request(**payload.model_dump(),buyer_company_id=user.company_id)
    db.add(req);db.commit();db.refresh(req)
    return {"id":req.id,"status":req.status}

@app.get('/api/requests')
def list_requests(db:Session=Depends(db_session),user:User=Depends(current_user)):
    requests=db.scalars(select(Request).join(Material).where((Request.buyer_company_id==user.company_id)|(Material.company_id==user.company_id)).order_by(Request.id.desc())).all()
    return [{"id":r.id,"material_id":r.material_id,"requested_quantity":r.requested_quantity,"status":r.status,"message":r.message} for r in requests]

@app.get('/api/ai/status')
def ai_status(user:User=Depends(current_user)):
    return {"configured":configured(),"provider":settings().llm_provider,"model":settings().llm_model if configured() else None}

@app.get('/api/ai/history')
def ai_history(db:Session=Depends(db_session),user:User=Depends(current_user)):
    rows=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id).order_by(ChatMessage.id.desc()).limit(100)).all()
    return [{"role":msg.role,"content":msg.content} for msg in reversed(rows)]

@app.delete('/api/ai/history')
def clear_ai_history(db:Session=Depends(db_session),user:User=Depends(current_user)):
    rows=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id)).all()
    for msg in rows:db.delete(msg)
    db.commit()
    return {"deleted":len(rows)}

@app.post('/api/ai/chat')
async def ai_chat(payload:MessageIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if not configured():raise HTTPException(503,"AI provider not configured. Set LLM_API_KEY in backend/.env")
    previous=db.scalars(select(ChatMessage).where(ChatMessage.user_id==user.id).order_by(ChatMessage.id.desc()).limit(8)).all()
    messages=[{"role":m.role,"content":m.content[:2000]} for m in reversed(previous)] + [{"role":"user","content":payload.message}]
    try:answer=await chat(messages,payload.language)
    except Exception:raise HTTPException(502,"AI provider unavailable. Check configuration or retry")
    db.add_all([ChatMessage(user_id=user.id,role="user",content=payload.message),ChatMessage(user_id=user.id,role="assistant",content=answer)])
    db.commit();return {"answer":answer}
