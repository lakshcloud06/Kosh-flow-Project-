import React from "react";
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";

const Plot = createPlotlyComponent(Plotly);

export default function PlotlyChart(props) {
  return (
    <Plot
      {...props}
      useResizeHandler={true}
      style={{ width: "100%", height: "100%", ...props.style }}
    />
  );
}
