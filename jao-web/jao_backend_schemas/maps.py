from typing import Optional

from pydantic import BaseModel


class AreaFrequencyProperties(BaseModel):
    # TODO: this should have area_code: str (called areacd in our geojson file)
    area_name: str
    frequency: Optional[float] = None

class AreaFrequenciesResponse(BaseModel):
    area_frequencies: list[AreaFrequencyProperties]
