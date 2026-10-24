from pydantic import BaseModel, ConfigDict, EmailStr, Field
# Email checks are kept dependency-free via a validator.
from pydantic import field_validator

class Register(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=10, max_length=128)
    company_name: str = Field(min_length=2, max_length=180)
    role: str = "factory"
    @field_validator("email")
    @classmethod
    def email_check(cls,v):
        if "@" not in v or "." not in v.split("@")[-1]: raise ValueError("Invalid email")
        return v.strip().lower()

class Login(BaseModel):
    email: str
    password: str

class MaterialIn(BaseModel):
    name: str = Field(min_length=2,max_length=200)
    category: str = Field(min_length=2,max_length=100)
    description: str = Field(default="",max_length=5000)
    quantity: float = Field(gt=0,le=1e12)
    unit: str = Field(default="t",pattern="^(t|kg)$")
    chemical_properties: str = Field(default="",max_length=3000)
    hazard_class: str = Field(default="unknown",max_length=60)
    lab_verified: bool = False
    price_per_unit: float | None = Field(default=None,ge=0)

class MaterialOut(MaterialIn):
    id: int
    company_id: int
    status: str
    is_demo: bool
    model_config = ConfigDict(from_attributes=True)

class RequestIn(BaseModel):
    material_id: int
    requested_quantity: float = Field(gt=0)
    message: str = Field(default="",max_length=1500)

class MessageIn(BaseModel):
    message: str = Field(min_length=1,max_length=2000)
    language: str = Field(default="ru",pattern="^(ru|kk|en)$")

class EconomyIn(BaseModel):
    quantity: float = Field(ge=0)
    sale_price_per_unit: float = Field(ge=0)
    processing_per_unit: float = Field(ge=0)
    transport_per_unit: float = Field(ge=0)
    storage_per_unit: float = Field(ge=0)
    other_cost: float = Field(ge=0)
