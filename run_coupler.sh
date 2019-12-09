#!/bin/sh
#SBATCH -t 2-00:00                            # time (day-hours:minutes)
#SBATCH -c 64                                 # number of cores
#SBATCH -N 1                                  # ensures all cores are on one machine
#SBATCH --mem=256000                          # memory pool for all cores (in MB)
#SBATCH -p unrestricted                       # partition
#SBATCH -o run_coupler.out                    # out file
#SBATCH -e run_coupler.err                    # error log file
#SBATCH --job-name=run_coupler                # job name
#SBATCH --mail-type=END,FAIL                  # email if job ends or fails
#SBATCH --mail-user=tim_menke@g.harvard.edu   # your email if you want job updates

module load centos6/0.0.1-fasrc01
module load Anaconda3/5.0.1-fasrc01
module load mathematica/11.1.1-fasrc01
# module load mathematica/11.3.0-fasrc01

source activate Qcirc

python circuit_searcher.py

echo Finished!
