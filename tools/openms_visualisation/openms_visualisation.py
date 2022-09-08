import argparse
import sys
from pyopenms import MSExperiment, MzMLFile, DRange1, DPosition1
import pandas as pd
import numpy as np
import datashader as ds
import holoviews as hv
import holoviews.operation.datashader as hd
from holoviews.plotting.util import process_cmap
from holoviews import opts, dim


def main(argv):
    parser = argparse.ArgumentParser(description="Visualise mzML data.")
    parser.add_argument("--input_file", type=str, help="Path to mzML file.")
    parser.add_argument("--output_file", type=str, help="Path to output HTML file.")
    args = parser.parse_args()

    hv.extension('bokeh')

    exp = MSExperiment()
    loader = MzMLFile()
    loadopts = loader.getOptions()
    loadopts.setMSLevels([1])
    loadopts.setSkipXMLChecks(True)
    loadopts.setIntensity32Bit(True)
    loadopts.setIntensityRange(DRange1(DPosition1(5000), DPosition1(sys.maxsize)))
    loader.setOptions(loadopts)
    loader.load(args.input_file, exp)
    exp.updateRanges()
    expandcols = ["RT", "mz", "inty"]

    spectraarrs2d = exp.get2DPeakDataLong(exp.getMinRT(), exp.getMaxRT(), exp.getMinMZ(), exp.getMaxMZ())
    spectradf = pd.DataFrame(dict(zip(expandcols, spectraarrs2d)))
    spectradf = spectradf.set_index(["RT", "mz"])

    maxrt = spectradf.index.get_level_values(0).max()
    minrt = spectradf.index.get_level_values(0).min()
    maxmz = spectradf.index.get_level_values(1).max()
    minmz = spectradf.index.get_level_values(1).min()

    def new_bounds_hook(plot, elem):
        x_range = plot.state.x_range
        y_range = plot.state.y_range
        x_range.bounds = minrt, maxrt
        y_range.bounds = minmz, maxmz

    points = hv.Points(spectradf, kdims=['RT', 'mz'], vdims=['inty'], label="Full scan of mass spectrometry data").opts(
        fontsize={'title': 16, 'labels': 14, 'xticks': 6, 'yticks': 12},
        color=np.log(dim('int')),
        colorbar=True,
        cmap='Magma',
        width=1000,
        height=1000,
        tools=['hover'])

    raster = hd.rasterize(points, cmap=process_cmap("blues", provider="bokeh"), aggregator=ds.sum('inty'),
                          cnorm='log', alpha=10, min_alpha=0
                          ).opts(active_tools=['box_zoom'], tools=['hover'], hooks=[new_bounds_hook]
                          ).opts(plot=dict(height=800, responsive=True,
                                           xlabel="Retention time (rt)", ylabel="mass/charge (m/z)"
                                          )
                                )

    hd.dynspread(raster, threshold=0.7, how="add", shape="square")
    hv.save(raster, args.output_file)
    return 0


if __name__ == "__main__":
    main(argv=sys.argv[1:])
