import os, sys
import numpy as np
import glob
import matplotlib.pyplot as plt

#TRANSLATION TABLE#
RODS={"110":"53274.txt",
"111":"53274.txt",
"112":"53274.txt",
"961":"53274.txt",
"962":"53274.txt",
"963":"53274.txt",
"964":"53274.txt",
"965":"53274.txt",
"966":"53274.txt",
"967":"53274.txt",
"968":"53274.txt"
}


def GetCorrections(f):
	t_expansion=None
	cor=[]
	for line in f:
		sline=line.split()
		if len(sline)==0:
			continue
		if sline[0]=="#":
			rodname=sline[1]
			temp=float(sline[2])
			t_expansion=float(sline[3])
			s_const=float(sline[4])
		else:
			try:
				m=float(sline[0])
				c=float(sline[1])
			except:
				pass
			else:
				cor.append([m,c])
	return rodname,cor,temp,t_expansion,s_const
	

class RodCorrector(object):
	def __init__(self,fname):
		f=open(fname)
		self.rod,self.cor,self.temp,self.t_exp,self.s_cont=GetCorrections(f)
		f.close()
		self.cor=np.array(self.cor)
		self.done=0
		self.mean_marks=0
	def Correct(self,temp,h,zs):
		self.done+=1
		reading=h-zs
		#find nearest marks#
		test=np.fabs(self.cor[:,0]-reading)
		I=np.where(test<0.15)[0]
		cor=0
		for j in I:
			cor+=self.cor[j,1]*(1.0+self.t_exp*(temp-self.temp))/I.size
		new=h+cor
		self.mean_marks=self.mean_marks*(self.done-1)/float(self.done)+I.size/float(self.done)
		return new


def GetData(f,rods):
	stretches=[]
	line=f.readline()
	stretch=Stretch()
	msg=""
	while len(line)>0:
		sline=line.split()
		if "tilbagesigte" in line:
			if len(sline)>7:
				data=[float(sline[-2]),float(sline[-4])]
				rod=sline[-7]
			else:
				data=[float(sline[-2])]
				rod=sline[-5]
			if rods.has_key(rod):
				zs=rods[rod]
			else:
				zs=0
				msg+="Zeroshift of rod %s not found!\n" %rod
			stretch.AddBack(data,zs,rod)
		elif "fremsigte" in line:
			if len(sline)>9:
				data=[float(sline[-6]),float(sline[-4])]
				
				rod=sline[-9]
			else:
				data=[float(sline[-4])]
				rod=sline[-7]
			if rods.has_key(rod):
				zs=rods[rod]
			else:
				zs=0
				msg+="Zeroshift of rod %s not found!\n" %rod
			stretch.AddForward(data,zs,rod)	
		elif len(sline)>0 and sline[0]=="T:":
			stretch.AddTemp(float(sline[1]))
		elif len(sline)>0 and sline[0]=="#":
			stretch.AddTemp(float(sline[8]))
			stretch.SetPoints(sline[1],sline[2])
			stretch.SetDistance(float(sline[5]))
			stretches.append(stretch)
		
			stretch=Stretch()
		line=f.readline()
	return stretches,msg
	
class Stretch(object):
	def __init__(self):
		self.back=np.empty((0,3))
		self.forward=np.empty((0,3))
		self.temp=np.empty((0,))
		self.p1=None
		self.p2=None
		self.distance=0
		self.forward_rods=[]
		self.back_rods=[]
		
	def SetPoints(self,p1,p2):
		self.p1=p1
		self.p2=p2
	def SetDistance(self,d):
		self.distance=d
	def GetPoints(self):
		return self.p1,self.p2
	def AddBack(self,data,zs,rod):
		if len(data)==1:
			data.append(-999)
		data.append(zs)
		self.back=np.vstack((self.back,data))
		self.back_rods.append(rod)
	def AddForward(self,data,zs,rod):
		if len(data)==1:
			data.append(-999)
		data.append(zs)
		self.forward=np.vstack((self.forward,data))
		self.forward_rods.append(rod)
	def AddTemp(self,t):
		self.temp=np.append(self.temp,[t]*(self.back.shape[0]-self.temp.shape[0]))
	def ApplyCorrection(self,rods=None):
		new_back=np.ones_like(self.back)*-999
		new_forward=np.ones_like(self.forward)*-999
		if (self.back[:,1]<0).any():
			do=1
		else:
			do=2
		msg=""
		func_forward=None
		func_back=None
		for i in range(do):
			for j in range(self.back.shape[0]):
				frod=self.forward_rods[j]
				brod=self.back_rods[j]
				if rods is not None:
					if frod in rods:
						func_forward=rods[frod].Correct
					if brod in rods:
						func_back=rods[frod].Correct
				if func_forward is None:
					msg+="%s to %s, setup: %d, rod %s not found. Using standad correction.\n" %(self.p1,self.p2,j+1,frod)
					func_forward=StandardCorrection
				if func_back is None:
					msg+="%s to %s, setup: %d, rod %s not found. Using standad correction.\n" %(self.p1,self.p2,j+1,brod)
					func_back=StandardCorrection
				new_back[j,i]=func_back(self.temp[j],self.back[j,i],self.back[j,2])
				new_forward[j,i]=func_forward(self.temp[j],self.forward[j,i],self.forward[j,2])
		return new_back,new_forward,msg
		
	def GetHdiff(self,back=None,forw=None):
		if back is None:
			back=self.back
			forw=self.forward
		if back.shape!=forw.shape:
			print("Uoops, mismatching shapes!")
			return -999
		if (back[:,1]<0).any():
			do=2
		else:
			do=1
		hdiff=back[:,:do].mean()-forw[:,:do].mean()
		return hdiff
			
		
def StandardCorrection(temp,h,zs):
	new=((h-zs)*(1.000003+0.83*(10**-6)*(temp-20))+zs)
	return new

def GetRods(f):
	rods=dict()
	line=f.readline()
	while len(line)>0:
		sline=line.split()
		if len(sline)==0:
			line=f.readline()
			continue
		if sline[0]=="*":
			return rods
		if len(sline)==4 and "nulpunktsfejl" in line.lower():
			rods[sline[0][:-1]]=float(sline[-2])
		line=f.readline()
	return rods
	

def main(args):
	#f=open(args[1])
	#cor,t_exp,s_const=GetCorrections(f)
	#f.close()
	files=glob.glob(args[1])
	ndiffs=[]
	diffs=[]
	ndiffs2=[]
	diffs2=[]
	print("Setting up rod translations:")
	rod_translations={}
	for rod in RODS.keys():
		print("%s is %s." %(rod,RODS[rod]))
		rod_translations[rod]=RodCorrector(RODS[rod])
	for fname in files:
		
		try:
			f=open(fname)
		except:
			continue
		line=f.readline()
		if "MGL" in line:
			print("Reading %s" %fname)
			rods=GetRods(f)
			stretches,msg=GetData(f,rods)
			if len(msg)>0:
				print msg
			print("Got %d stretches" %len(stretches))
			for s in stretches:
				bc,fc,msg=s.ApplyCorrection()
				bc1,fc1,msg=s.ApplyCorrection(rod_translations)
				if len(msg)>0:
					print msg
				h1,h2,h3=s.GetHdiff(),s.GetHdiff(bc,fc),s.GetHdiff(bc1,fc1)
				diff=(h1-h2)*1000
				diff2=(h1-h3)*1000.0
				if abs(diff)>np.sqrt(s.distance/1000.0)*0.5:
					p1,p2=s.GetPoints()
					print("file: %s, stretch: %s->%s, diff: %.4f mm, dist: %.2f m" %(fname,p1,p2,diff,s.distance))
					print("Without: %.6f m, with: %.6fm" %(h1,h2))
					print("Mean-temp: %.2f deg C" %s.temp.mean())
				ndiffs.append(abs(diff)/np.sqrt(s.distance/1000.0))
				diffs.append(diff)
				ndiffs2.append(abs(diff2)/np.sqrt(s.distance/1000.0))
				diffs2.append(diff2)
		else:
			print("%s not (new) MGL file" %fname)
		f.close()
	print("Mean diff: %.6f mm" %np.mean(diffs))
	for rod in rod_translations.keys():
		C=rod_translations[rod]
		if C.done>0:
			print("Mean number of marks for rod %s: %.3f" %(rod,C.mean_marks))
	plt.subplot(2,2,1)
	plt.title("Afstandsnormaliserede forskelle - bedste rette linie")
	plt.hist(ndiffs)
	plt.xlabel("mm/sqrt(km)")
	plt.subplot(2,2,2)
	plt.title("Forkskelle - bedste rette linie")
	plt.xlabel("mm")
	plt.hist(diffs)
	plt.subplot(2,2,3)
	plt.title(u"Afstandsnormaliserede forskelle - med m\u00E6rker")
	plt.hist(ndiffs2)
	plt.xlabel("mm/sqrt(km)")
	plt.subplot(2,2,4)
	plt.title(u"Forkskelle - med m\u00E6rker")
	plt.hist(diffs2)
	plt.xlabel("mm")
	plt.figure()
	plt.title("Rod: %s" %C.rod)
	plt.plot(C.cor[:,0],C.cor[:,1]*10**6)
	plt.xlabel("Mark [m]")
	plt.ylabel("Correction [um]")
	plt.show()

if __name__=="__main__":
	main(sys.argv)
	