import os
import sys
import subprocess
def install(package) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install('pandas==1.5.3')    
install('awswrangler')
install('tqdm')
install('botocore')
install('pandas-profiling')
install('s3fs')
install('fsspec')
install('japanize-matplotlib')

from glob import glob
import datetime as dt
import numpy as np
import pandas as pd
import argparse
import datetime
import seaborn as sns
import japanize_matplotlib

from ydata_profiling import ProfileReport
import ydata_profiling as pdp



def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str)
    parser.add_argument('--output_dir', type=str, default=".")
    parser.add_argument('--output_file', type=str)
    args, _ = parser.parse_known_args()
    return args


def profiling(input_file: str) -> pdp.ProfileReport:
    sns.set(font='IPAexGothic')
    df = pd.read_csv(input_file, header=0)
    profile = pdp.ProfileReport(df)
    
    return profile


if __name__ == "__main__":
    args = arg_parse() #引数を受け取る
    
    profile = profiling(args.input_file)
    
    output_filename = os.path.join(args.output_dir, args.output_file)
    profile.to_file(output_filename)

    






