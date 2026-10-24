from sqlalchemy import select
from app.database import Base,engine,SessionLocal
from app.models import Company,Material
Base.metadata.create_all(engine)
SAMPLES=[("Demo Phosphogypsum Batch A","phosphogypsum",8000,"Synthetic example; composition unverified"),("Demo Steel Scrap","metal",240,"Sorted scrap example"),("Demo Slag","slag",1100,"Synthetic mineral slag")]
with SessionLocal() as db:
    company=db.scalar(select(Company).where(Company.name=="DEMO Industrial Plant (fictional)"))
    if not company:
        company=Company(name="DEMO Industrial Plant (fictional)",industry="Industrial",city="Taraz",is_demo=True)
        db.add(company);db.flush()
    for name,category,quantity,description in SAMPLES:
        if not db.scalar(select(Material).where(Material.company_id==company.id,Material.name==name)):
            db.add(Material(company_id=company.id,name=name,category=category,quantity=quantity,unit="t",description=description,is_demo=True))
    db.commit()
print("Synthetic demo material records seeded idempotently")
