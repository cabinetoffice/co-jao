from typing import List, Dict, Any

from plotly.graph_objs import Figure
from pydantic import BaseModel


class PlotlyFiguresResponse(BaseModel):
    plotly_figures: List[Dict[str, Any]]

    def get_figures(self):
        figures = [Figure(**plot_kwargs) for plot_kwargs in self.plotly_figures]
        return figures
