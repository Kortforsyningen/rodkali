import sys,os
import numpy as np
import matplotlib.pyplot as plt
f=open(sys.argv[1])
data=f.read().replace(";"," ")
f.close()
g=open(sys.argv[2],"w")
g.write("#\n")
ts=[]
for line in data.splitlines():
	sline=line.split()
	if len(sline)>5:
		try:
			float(sline[0])
		except:
			continue
		else:
			try:
				t=float(sline[4])
				m=float(sline[5])
				c=float(sline[7])
			except:
				continue
			if len(ts)>0 and abs(t-np.mean(ts))>1.0:
				continue
			ts.append(t)
			g.write("%.3f %.12f\n" %(m,c*(10**-6)))

print("Temp: %.2f, sd: %.3f" %(np.mean(ts),np.std(ts)))
plt.hist(ts)
plt.show()
g.close()

				
	