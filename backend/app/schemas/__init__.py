from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status indicator", examples=["ok"])
    service: str = Field(..., description="Service name", examples=["JalNetra API"])
    version: str = Field(..., description="API semantic version", examples=["2.0.0"])


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error description")


class ErrorResponse(BaseModel):
    error: ErrorDetail
