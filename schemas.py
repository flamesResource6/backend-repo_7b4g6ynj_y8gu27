"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict
from datetime import datetime

# ------------------------------
# Water Quality Sampling Schemas
# ------------------------------

class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")

class SampleFile(BaseModel):
    filename: str
    url: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None

class WaterSample(BaseModel):
    """
    Water quality sample schema
    Collection name: "watersample"
    """
    # Sample identifiers/metadata
    scenario: str = Field(..., description="Scenario tag (e.g., dry, monsoon, upstream, industrial)")
    site_name: Optional[str] = Field(None, description="Sampling site name or code")
    collected_at: datetime = Field(..., description="Timestamp of collection (UTC)")

    # Geospatial
    location: Location

    # Core parameters
    ph: Optional[float] = Field(None, ge=0, le=14, description="pH value")
    dissolved_oxygen_mg_l: Optional[float] = Field(None, ge=0, description="Dissolved Oxygen (mg/L)")
    turbidity_ntu: Optional[float] = Field(None, ge=0, description="Turbidity (NTU)")

    # Heavy metals concentrations (mg/L) - dynamic dict
    metals_mg_l: Optional[Dict[str, float]] = Field(
        default=None,
        description="Dictionary of metal name to concentration (mg/L)"
    )

    # Extras
    notes: Optional[str] = Field(None, description="Freeform notes about the sample")
    files: Optional[List[SampleFile]] = Field(default=None, description="Associated file metadata (images, sensors)")


# Optional: Simple analysis result schema for returning summaries
class ScenarioSummary(BaseModel):
    scenario: str
    count: int
    avg_ph: Optional[float] = None
    avg_do: Optional[float] = None
    avg_turbidity: Optional[float] = None


# Example schemas (kept for reference, not used by app)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
