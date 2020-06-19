import numpy as np

from utils.structures import *
from utils.structures import Database
from typing import List
import math

# def switch_X(F):
#     return(apply(t(F[,ncol(F):1]),2,rev))
# -> not neede in numpy axis are in good order already

# remove negative values
def remove_negative(v,val):
    v[v<0] = val
    return v

def combine_results(results : List[SerialResult]):

    names = ('cent.x', 'cent.y', 'snr', 'iter', 'sum', 'mean', 'var', 'std', 'skew', 'kurt', 'bckg')
    database  = Database(init_value=0, nrows=0, ncols=11, col_names=names )
    discarded = Database(init_value=0, nrows=0, ncols=11, col_names=names )
    
    stats = Stats()

    for result in results:
        database = database.concatenate(result.database)
        discarded = database.concatenate(result.discarded)

        stats.started  += result.stats.started
        stats.nulldata += result.stats.nulldata
        stats.notenough+= result.stats.notenough
        stats.notbright+= result.stats.notbright
        stats.nocentre += result.stats.nocentre
        stats.maxiter  += result.stats.maxiter
        stats.miniter  += result.stats.miniter
        stats.lowsnr   += result.stats.lowsnr
        stats.ok       += result.stats.ok
        stats.notright += result.stats.notright

    return SerialResult(database=database, discarded=discarded, stats=stats)


def rms(X, predicted=None):
    if predicted is None:
        return np.sqrt(np.sum(X**2)/len(X))
    return np.sqrt(
            np.sum(
                (normalize(predicted) - normalize(X))**2
                ) / predicted.size
            )

def neighbor_check(first_point, second_point):
    dist = np.linalg.norm( np.array(first_point) - np.array(second_point) )
    if dist == 1 or dist == math.sqrt(2):
        return True
    return False

def psnr(data, bg_median, noise_dispersion):
    peak = data.max()
    bg_median = float(bg_median)
    noise_dispersion = float(noise_dispersion)
    return round((peak-bg_median) / math.sqrt(peak - bg_median + noise_dispersion), 2)

def normalize(data):
    return data/data.max()