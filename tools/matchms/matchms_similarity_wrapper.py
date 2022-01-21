import argparse
import sys

from matchms import calculate_scores
from matchms.importing import load_from_mgf, load_from_msp
from matchms.similarity import (
    CosineGreedy,
    CosineHungarian,
    ModifiedCosine,
    ParentMassMatch,
    FingerprintSimilarity
)
from pandas import DataFrame


def convert_precursor_mz(spectrum):
    """
    Check the presence of precursor m/z since it is needed for ModifiedCosine similarity metric. Convert to float if
    needed, raise error if missing.
    """

    if "precursor_mz" in spectrum.metadata:
        metadata = spectrum.metadata
        metadata["precursor_mz"] = float(metadata["precursor_mz"])
        spectrum.metadata = metadata
        return spectrum
    else:
        raise ValueError("Precursor_mz missing. Apply 'add_precursor_mz' filter first.")


def main(argv):
    parser = argparse.ArgumentParser(description="Compute MSP similarity scores")
    parser.add_argument("--symmetric", dest="symmetric", action='store_true', help="Computation is symmetric.")
    parser.add_argument("--ref", dest="references_filename", type=str, help="Path to reference spectra library.")
    parser.add_argument("--ref_format", dest="references_format", type=str,
                        help="Reference spectra library file format.")
    parser.add_argument("--queries", dest="queries_filename", type=str, help="Path to query spectra.")
    parser.add_argument("--queries_format", dest="queries_format", type=str, help="Query spectra file format.")
    parser.add_argument("--metric", dest="similarity_metric", type=str, help='Metric to use for matching.')
    parser.add_argument("--tolerance", type=float, help="Tolerance to use for peak matching.")
    parser.add_argument("--mz_power", type=float, help="The power to raise mz to in the cosine function.")
    parser.add_argument("--intensity_power", type=float, help="The power to raise intensity to in the cosine function.")
    parser.add_argument("--similarity_measure", type=str,
                        help="Choose similarity measure from 'cosine', 'dice', 'jaccard'.")
    parser.add_argument("--output_scores", dest="output_filename_scores", type=str,
                        help="Path where to store the output .tsv scores.")
    parser.add_argument("--output_matches", dest="output_filename_matches", type=str,
                        help="Path where to store the output .tsv matches.")
    args = parser.parse_args()

    if args.queries_format == 'msp':
        queries_spectra = list(load_from_msp(args.queries_filename))
    elif args.queries_format == 'mgf':
        queries_spectra = list(load_from_mgf(args.queries_filename))
    else:
        raise ValueError(f'File format {args.queries_format} not supported for query spectra.')

    if args.symmetric:
        reference_spectra = []
    else:
        if args.references_format == 'msp':
            reference_spectra = list(load_from_msp(args.references_filename))
        elif args.references_format == 'mgf':
            reference_spectra = list(load_from_mgf(args.references_filename))
        else:
            raise ValueError(f'File format {args.references_format} not supported for reference spectra library.')

    if args.similarity_metric == 'CosineGreedy':
        similarity_metric = CosineGreedy(args.tolerance, args.mz_power, args.intensity_power)
    elif args.similarity_metric == 'CosineHungarian':
        similarity_metric = CosineHungarian(args.tolerance, args.mz_power, args.intensity_power)
    elif args.similarity_metric == 'ModifiedCosine':
        similarity_metric = ModifiedCosine(args.tolerance, args.mz_power, args.intensity_power)
        reference_spectra = list(map(convert_precursor_mz, reference_spectra))
        queries_spectra = list(map(convert_precursor_mz, queries_spectra))
    elif args.similarity_metric == 'ParentMassMatch':
        similarity_metric = ParentMassMatch(args.tolerance)
        # check if parent mass is present
    elif args.similarity_metric == 'FingerprintSimilarity':
        similarity_metric = FingerprintSimilarity(args.similarity_measure)
        # check if fingerprints are present (or set set_empty_scores arg)
    else:
        return -1

    print("Calculating scores...")
    scores = calculate_scores(
        references=queries_spectra if args.symmetric else reference_spectra,
        queries=queries_spectra,
        similarity_function=similarity_metric,
        is_symmetric=args.symmetric
    )

    write_outputs(args, scores)
    return 0


def write_outputs(args, scores):
    print("Storing outputs...")
    query_names = [spectra.metadata['name'] for spectra in scores.queries]
    reference_names = [spectra.metadata['name'] for spectra in scores.references]

    # Write scores to dataframe
    dataframe_scores = DataFrame(data=[entry["score"] for entry in scores.scores], index=reference_names, columns=query_names)
    dataframe_scores.to_csv(args.output_filename_scores, sep='\t')

    # Write number of matches to dataframe
    dataframe_matches = DataFrame(data=[entry["matches"] for entry in scores.scores], index=reference_names, columns=query_names)
    dataframe_matches.to_csv(args.output_filename_matches, sep='\t')


if __name__ == "__main__":
    main(argv=sys.argv[1:])
    pass
