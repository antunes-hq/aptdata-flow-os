from typing import Optional

from pydantic import BaseModel, Field

class SilverMatchModel(BaseModel):
    match_id: str = Field(..., description="UUID da partida")
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    date: str

class GoldTeamStatsModel(BaseModel):
    team: str
    total_goals_scored: int
    matches_played: int
