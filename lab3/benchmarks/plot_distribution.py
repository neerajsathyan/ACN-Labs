import matplotlib.pyplot as plt
import random
import numpy as np
from collections import defaultdict

def count_occurence(values, n):
    
    unique = np.unique(values)

    cum_res = {}
    for uni in unique:
        count = values.count(uni)
        cum_res[uni] = count / n
        
    return cum_res

######################### INSERT AVG PING RESULTS HERE ##############################
AVGs = [0.57, 1.192, 1.365, 1.771, 1.318, 1.738, 1.674, 1.479, 1.292, 1.652, 1.35, 1.661, 1.299, 1.36, 1.378, 0.651, 
        0.569, 0.743, 0.727, 0.718, 0.718, 0.759, 0.775, 0.901, 0.763, 0.719, 0.847, 0.705, 0.605, 0.393, 0.824, 0.904, 
        0.687, 0.789, 0.705, 0.915, 0.767, 0.871, 0.722, 0.643, 0.773, 0.869, 0.762, 0.543, 0.543, 0.815, 0.752, 0.797, 
        0.716, 0.885, 0.69, 0.643, 0.635, 0.791, 0.386, 0.71, 0.703, 0.756, 0.806, 0.669, 0.723, 0.799, 0.836, 0.625, 
        0.627, 0.418, 0.493, 0.774, 0.842, 0.808, 0.829, 0.669, 0.879, 0.784, 0.789, 0.396, 0.709, 0.66, 0.65, 0.704, 
        0.749, 0.734, 0.746, 0.726, 0.828, 0.585, 0.76, 0.839, 0.75, 0.774, 0.633, 0.71, 0.32, 0.627, 0.627, 0.809, 
        0.75, 0.926, 0.806, 0.416, 0.616, 0.734, 0.735, 0.867, 0.695, 0.406, 0.868, 0.808, 0.761, 0.63, 0.857, 0.796, 
        0.75, 0.855, 0.463, 0.661, 0.604, 0.701, 0.644, 0.28]



n = len(AVGs)
width = 0.01

round_AVGs = [round(AVG, 2) for AVG in AVGs]
cum_AVGs = count_occurence(round_AVGs, n)


plt.bar(cum_AVGs.keys(), cum_AVGs.values(), width=width, label='shortest path')
plt.xlabel('Average ping in ms')
plt.ylabel('Fraction server pairs')
plt.savefig('Average_ping_distribution_two_level')
plt.show()



######################### INSERT iperf RESULTS HERE ##############################
IPERFs = [70.0, 58.9, 54.3, 48.3, 47.6, 48.1, 46.8, 53.1, 51, 51.8, 52.6, 51.8, 
          50.4, 48.1, 49.1, 55, 54.5, 47.8, 47.1, 52.5, 48.9, 50.4, 52.1, 49.2,
          49.8, 52.8, 52.3, 52.5, 53.3, 67.9, 50.2 , 51.6, 50.9, 51.6, 61.5, 50.3,
          49.2, 49.3, 47.7, 49.2, 50.1, 49.9, 48.1, 49.5, 46.8, 50.9, 48.1, 48.9,
          47.4, 50.2, 47.5, 47.2, 50.8, 47.5, 61.1, 58.6, 57.9, 48.1, 50.9, 50.7, 
          50.8, 51.7, 49.2, 50.3, 48.5, 55.1, 55.3, 50.2, 48.1, 50.5, 49.4, 50.3, 
          50.7, 46.4, 49.9, 70.5, 52.5, 52.5, 52.5, 52.4, 52.9, 52.9, 52.6, 50.6,
          50.4, 51, 50.5, 51.5, 51.5, 50.9, 51.1, 51.4, 65, 57.1, 56.8, 52, 49.2, 
          51.9, 51, 57.9, 57.5, 51.1, 50.6, 47.6, 50.9, 69.2, 50.5, 50.6, 50.7, 
          50.2, 52, 50.6, 51.6, 51.5, 61.7, 50.3, 50.9, 50.1, 52.5]

width = 0.1

round_IPERFs = [IPERF for IPERF in IPERFs]

unique = np.unique(round_IPERFs)

cum_IPERFs = {}
for uni in unique:
    count = round_IPERFs.count(uni)
    cum_IPERFs[uni] = count


plt.bar(cum_IPERFs.keys(), cum_IPERFs.values(), width=width, label='shortest path')
plt.xlabel('Throughput in Gbits/sec')
plt.ylabel('Number of server pairs')
plt.savefig('Average_iperf_distribution_two_level')
plt.show() 

