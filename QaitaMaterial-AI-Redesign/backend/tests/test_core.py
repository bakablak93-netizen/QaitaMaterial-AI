import os
os.environ["DATABASE_URL"]="sqlite:///./test_qaita.db"
os.environ["JWT_SECRET_KEY"]="test-secret-do-not-use-in-production"
from fastapi.testclient import TestClient
from app.main import app
from app.services.analysis import economy, analyze
from app.schemas import EconomyIn
from types import SimpleNamespace

def test_health():
    with TestClient(app) as c:
        assert c.get('/api/health').json()['status']=='ok'

def test_auth_and_materials():
    with TestClient(app) as c:
        account={'name':'Test User','email':'test1234@example.com','password':'strong-pass-123','company_name':'Test Company 1234'}
        r=c.post('/api/auth/register',json=account)
        assert r.status_code in (200,409)
        login=c.post('/api/auth/login',json={'email':account['email'],'password':account['password']})
        assert login.status_code==200
        headers={'Authorization':'Bearer '+login.json()['access_token']}
        body={'name':'Test slag','category':'slag','quantity':20,'unit':'t'}
        created=c.post('/api/materials',json=body,headers=headers)
        assert created.status_code==201
        mid=created.json()['id']
        assert c.get('/api/materials/'+str(mid)+'/analysis',headers=headers).status_code==200
        assert c.patch('/api/materials/'+str(mid),json={**body,'quantity':30},headers=headers).json()['quantity']==30
        assert c.delete('/api/materials/'+str(mid),headers=headers).json()['deleted']
        assert c.get('/api/ai/status',headers=headers).json()['configured'] is False

def test_economy():
    r=economy(EconomyIn(quantity=10,sale_price_per_unit=100,processing_per_unit=10,transport_per_unit=5,storage_per_unit=2,other_cost=20))
    assert r['net']==810

def test_phosphogypsum_safety_gate():
    m=SimpleNamespace(id=1,name='phosphogypsum',category='phosphogypsum',description='',chemical_properties='',hazard_class='unknown',lab_verified=False)
    r=analyze(m)
    assert 'radiological screening' in r['missing_information']
    assert all(x['status']=='requires_verification' for x in r['recommendations'])

def test_chat_history_and_clear():
    from app.database import SessionLocal
    from app.models import ChatMessage
    with TestClient(app) as c:
        account={'name':'History User','email':'chat.history.testing@example.com','password':'strong-pass-123','company_name':'History Company for Tests'}
        response=c.post('/api/auth/register',json=account)
        assert response.status_code in (200,409)
        token=c.post('/api/auth/login',json={'email':account['email'],'password':account['password']}).json()['access_token']
        h={'Authorization':'Bearer '+token}
        uid=c.get('/api/me',headers=h).json()['id']
        with SessionLocal() as db:
            db.add(ChatMessage(user_id=uid,role='user',content='hello from test'))
            db.commit()
        response=c.get('/api/ai/history',headers=h)
        assert response.status_code==200
        assert any(row['content']=='hello from test' for row in response.json())
        response=c.delete('/api/ai/history',headers=h)
        assert response.status_code==200
        assert c.get('/api/ai/history',headers=h).json()==[]
        assert c.get('/api/ai/history').status_code==401

def test_dashboard_category_quantities_are_normalized_to_tonnes():
    with TestClient(app) as c:
        account={'name':'Metric User','email':'metrics.testing@example.com','password':'strong-pass-123','company_name':'Metric Company for Tests'}
        response=c.post('/api/auth/register',json=account)
        assert response.status_code in (200,409)
        token=c.post('/api/auth/login',json={'email':account['email'],'password':account['password']}).json()['access_token']
        headers={'Authorization':'Bearer '+token}
        created=c.post('/api/materials',json={'name':'Copper stock measured kg','category':'copper-unit-test','quantity':2000,'unit':'kg'},headers=headers)
        assert created.status_code==201
        mid=created.json()['id']
        d=c.get('/api/dashboard',headers=headers).json()
        assert d['category_quantities']['copper-unit-test']>=2
        c.delete(f'/api/materials/{mid}',headers=headers)
