#!/usr/bin/python 
##################
##rodkali.py simlk, june 2012
##
##kald: rodkali.py <input_files> <output_dir>
##
##Opdater identiteter og konstanter nedenfor.
##
## LOG:
## 2012-10-25: Tag hensyn til negative input ved maaling af GPS stationer
################
import os, sys
import glob
from math import *
import time
VERSION="1.1 2012-10-25"
DEBUG=False
ND_VALUE=-999


	
class Rod(object):
	def __init__(self,name,data=None,zeroshift=None):
		self.name=name
		if data is not None:
			self.l0=data[0]
			self.m0=data[1]
			self.alpha_t=data[2]
			self.vg=data[3]
			self.t0=data[4]
			self.is_calibrated=True
		else:
			self.is_calibrated=False
		if zeroshift is not None:
			self.zeroshift=zeroshift
		else:
			self.zeroshift=None
	def Correct(self,temp,h):
		if self.zeroshift is None:
			raise Exception("Warning: rod %s, zeroshift not set!!" %self.name)
		else:
			zs=self.zeroshift
		sign=1
		#take negative input ('inversed') into consideration.
		if (h<0):
			sign=-1
			h=abs(h)
		h_real=h-zs
		h_corr=self.l0+h_real*(1+(self.m0+self.alpha_t*(temp-self.t0))*1e-6)+self.vg #see DE calibration report
		h_corr+=zs
		if DEBUG and (abs(h_corr-h)>0.00005 or sign<0):
			print("Rod: %s, before: %.7f m, after: %.7f m, zeroshift: %.4f m, sign: %d" %(self.name,h,h_corr,zs,sign))
			s=raw_input(":")
			if "stop" in s:
				sys.exit()
		return h_corr*sign
	#Standard correction used when rod parameters NOT defined below!#
	#ONLY a standard temperature expansion applied!# 
	def StandardCorrection(self,temp,h):
		if self.zeroshift is None:
			raise Exception("Warning: rod %s, zeroshift not set!!" %self.name)
		else:
			zs=self.zeroshift
		sign=1
		if (h<0):
			sign=-1
			h=abs(h)
		h_real=h-zs
		h_corr=h_real*(1+(0.8*1e-6)*(temp-20.0))
		h_corr+=zs
		return h_corr*sign
		
	def SetZeroshift(self,zs):
		self.zeroshift=zs

#ROD = [l_0 [m] , m_0 [ppm], alpha_T [ppm], v_G [m], T_0 [degC] ]   - see calibration report
#ALL terms related to zero-shift (l_0 and v_G ) are set to 0 - we handle those ourselves directly in the data gathering code.
#THUS the correction consists ONLY of a combined temperature and scale expansion coefficient acting on the nominal height (which is modified by zero-shift).
#THE sensitivity of the correction as a function of the absolute nominal height input is very small (e.g. +- 1mm in input has no significant effect on the correction).
#THIS change will only have significance in case two different rods are used for point attachments in each end of a stretch!
#ROD_53278=[0.0                ,4.81,      0.86 ,  0.0,    20.0]
ROD_53278=[0.0                ,8.48,      0.86 ,  0.0,    20.0]
#ROD_53274=[0.0                , 3.2 ,     0.83 ,   0.0,    20.0]
ROD_53274=[0.0                , 5.24 ,     0.83 ,   0.0,    20.1]
#ROD_53281=[0.0                , 6.89,     0.90,   0.0,    20.0]
ROD_53281=[0.0                , 7.85,     0.90,   0.0,    20.1]
#ROD_53369=[0.0                , 5.53,     0.79,   0.0,    20.0]
ROD_53369=[0.0                , 3.76,     0.79,   0.0,    20.0]
ROD_53273=[0.0                , 4.76 ,   1.08 ,   0.0,    20.1]
#ROD_15022=[0.0                , -2.96,   0.76,    0.0,    20.1]
ROD_15022=[0.0                , 0.76,   0.76,    0.0,    20.1]
#ROD_58620=[0.0                ,  1.17,   0.58,    0.0,    20.0]
ROD_58620=[0.0                ,  1.25,   0.58,    0.0,    20.1]
#ROD_53607=[0.0                ,  7.36,   0.72,    0.0,    20.1]
ROD_53607=[0.0                ,  7.44,   0.72,    0.0,    20.1]
#ROD_53119=[0.0                , 4.44,   0.79,     0.0,   19.9]
ROD_53119=[0.0                , 4.21,   0.79,     0.0,   20.1]
#ROD_13292=[0.0                , 1.12,    0.77,    0.0,    20.1]
ROD_13292=[0.0                , 1.79,    0.77,    0.0,    20.0]
ROD_34194=[0.0                , 5.3,     0.80,     0.0,   20.1]
ROD_12863=[0.0                , 11.82,  0.90,     0.0,   20.1]
ROD_60676=[0,0                , 0.39, 0.55,  0.0,        19.9]



		
#TRANSLATION TABLE#
RODS={
"110":  Rod("110",ROD_53278),
"111":  Rod("111",ROD_53274),
"112":  Rod("112",ROD_53281),
"113":  Rod("113",ROD_53369),
"120":  Rod("120",ROD_53273),
"121":  Rod("121",ROD_15022),
"132":  Rod("132",ROD_58620),
"123":  Rod("123",ROD_53607),
"130":  Rod("130",ROD_53119),
"131":  Rod("131",ROD_13292),
"122":  Rod("122",ROD_12863),
"135":  Rod("135",ROD_60676)
}
#"961":  Rod("961",ROD_53273),
#"962":  Rod("962",ROD_53273),
#"963":  Rod("963",ROD_53273),
#"964":  Rod("963",ROD_53273),
#"965":  Rod("965",ROD_53273),
#"966":  Rod("966",ROD_53273),
#"967":  Rod("967",ROD_53273),
#"968":  Rod("968",ROD_53273)


###########################
##
## Class to redirect stdout
##
###########################
#TODO: add close method..... perhaps make it a global object.....
class RedirectStdout(object):
	def __init__(self,log_file):
		self.log_file=log_file
	def write(self,text):
		try:
			self.log_file.write(text)
		except:
			pass
		sys.__stdout__.write(text)
	

###############################
## Function that reads data from data-file
## This can be complicated due to 'hand-editing' of file!!!
###############################
def GetData(f,rods,n_lines):
	stretches=[]
	line=f.readline()
	stretch=Stretch()
	msg=""
	p1=None
	p2=None
	should_end=False
	while len(line)>0:
		n_lines+=1
		sline=line.split()
		if len(sline)==0:
			line=f.readline()
			continue
		if "tilbagesigte"==sline[0]:
			#len can be 6, 7, 8 or 9
			# 6 and 7 means single meas, 8 and 9 means double
			# 7 and 9 means start of new stretch!
			if should_end:
				msg+="We seem to have a deleted head around line %d\n" %n_lines
			if len(sline)>=8:
				data=[float(sline[-2]),float(sline[-4])]
				rod=sline[-7]
			else:
				data=[float(sline[-2])]
				rod=sline[-5]
			if len(sline)==7 or len(sline)==9:
				start_new=True
				stretch=Stretch()
				p1=sline[1]
			if rod in rods:
				rod_class=rods[rod]
			else:
				rod_class=None
				msg+="Rod %s not defined!\n" %rod
			stretch.AddBack(data,rod_class)
		elif "fremsigte"==sline[0]:
			#len can be 8 9 10 or 11 - 9 or 11 means we have an endpoint
			#8,9 means single meas, 10 or 11 means double meas.
			if len(sline)>=10:
				data=[float(sline[-6]),float(sline[-4])]
				rod=sline[-9]
			else:
				data=[float(sline[-4])]
				rod=sline[-7]
			if len(sline)==9 or len(sline)==11:
				should_end=True
				p2=sline[1]
			else:
				should_end=False
			if rod in rods:
				rod_class=rods[rod]
			else:
				rod_class=None
				msg+="Rod %s not defined!\n" %rod
			stretch.AddForward(data,rod_class)	
		elif len(sline)>0 and sline[0]=="T:":
			stretch.AddTemp(float(sline[1]))
		elif len(sline)>0 and sline[0]=="#":
			if not should_end:
				msg+="line: %d, %s -> %s, something wrong in data-formatting!\n"%(n_lines,sline[1],sline[2])
			should_end=False
			if p1!=sline[1] or p2!=sline[2]:
				msg+="line: %d, head says: %s -> %s, data says: %s -> %s\n" %(n_lines,sline[1],sline[2],p1,p2)
			stretch.SetHead(sline)
			#if head found - save and test (in stretch class)
			stretches.append(stretch)
		line=f.readline()
		
	return stretches,msg
	
class Stretch(object):
	def __init__(self):
		self.back=[]
		self.forward=[]
		self.temp=[]
		self.p1=None
		self.p2=None
		self.distance=0
		self.forward_rods=[]
		self.back_rods=[]
		self.all_double=True
		self.some_double=False
		self.head=None
	def SetHead(self,head):
		self.head=head
		self.AddTemp(float(head[8]))
		self.p1=head[1]
		self.p2=head[2]
		self.distance=float(head[5])
		if len(head)>9:
			self.nopst=int(head[-1])
			if self.nopst!=len(self.forward):
				raise Exception("%s->%s. Number of setups in head incosistent with data!" %(self.p1,self.p2))
		self.raw_hdiff=float(head[6])
		diff=abs(self.raw_hdiff-self.GetHdiff())
		if diff>1e-4:
			h1=sum([h[0] for h in self.forward])
			h2=sum([h[0] for h in self.back])
			print("Calulated from single meas: %.6f, saved: %.6f" %(h2-h1,self.raw_hdiff))
			raise Exception("%s->%s. Inconsistency %.4f mm between calculated hdiff and hdiff from head" 
			%(self.p1,self.p2,diff*1000))
			
	def GetPoints(self):
		return self.p1,self.p2
	def AddBack(self,data,rod):
		if len(data)==1:
			data.append(ND_VALUE)
			self.all_double=False
		else:
			self.some_double=True
		self.back.append(data)
		self.back_rods.append(rod)
	def AddForward(self,data,rod):
		if len(data)==1:
			data.append(ND_VALUE)
		self.forward.append(data)
		self.forward_rods.append(rod)
	#check that temps are connected to right measurement!#
	def AddTemp(self,t):
		if len(self.temp)<len(self.back):
			lots_of_temps=[t]*(len(self.back)-len(self.temp))
			self.temp.extend(lots_of_temps)
	def ApplyCorrection(self):
		ok=True
		new_back=[]
		new_forward=[]
		if self.some_double:			
			do=2
		else:
			do=1
		msg="Stretch: %s to %s\n" %(self.p1,self.p2)
		if self.some_double and not self.all_double:
			msg="Weirdness: Some double-double (precision) measured, but not all!\n"
			ok=False
		for j in range(len(self.back)):
			f_data=[]
			b_data=[]
			frod=self.forward_rods[j]
			brod=self.back_rods[j]
			if frod.is_calibrated:
				func_forward=frod.Correct
			else:
				msg+="setup: %d, rod not calibrated. Using standard correction.\n" %(j+1)
				func_forward=frod.StandardCorrection
				ok=False
			if brod.is_calibrated:
				func_back=brod.Correct
			else:
				msg+="setup: %d, rod not calibrated. Using standard correction.\n" %(j+1)
				func_back=brod.StandardCorrection
				ok=False
			for i in range(do):
				if (self.back[j][i]==ND_VALUE):
					f_data.append(ND_VALUE)
					b_data.append(ND_VALUE)
					continue
				#print("Back:")
				val=func_back(self.temp[j],self.back[j][i])
				b_data.append(val)
				#print val,new_back
				#print("Forw:")
				val=func_forward(self.temp[j],self.forward[j][i])
				f_data.append(val)
				#print val,new_forward
			new_forward.append(f_data)
			new_back.append(b_data)
		#print("back:\n%s\n%s\nforw:\n%s\n%s" %(new_back,self.back,new_forward,self.forward))
		return new_back,new_forward,msg,ok
		
	def GetHdiff(self,back=None,forw=None):
		if back is None:
			back=self.back
			forw=self.forward
		if len(back)!=len(forw):
			raise Exception("Uoops, mismatching shapes! Wrong formatting in data file")
		dh=0
		for i in range(len(forw)):
			dh_setup=0
			if self.some_double and (forw[i][1]!=ND_VALUE and back[i][1]!=ND_VALUE):
				dh_setup=(back[i][0]+back[i][1]-(forw[i][0]+forw[i][1]))*0.5
			else:
				dh_setup=(back[i][0]-forw[i][0])
			dh+=dh_setup
		return dh
			
		
def StandardCorrection(temp,h,zs=0):
	new=((h-zs)*(1.000003+0.83*(10**-6)*(temp-20))+zs)
	return new

################################
# Gets rods from data-file and copies header to output#
################################

	
def GetRods(f,out):
	rods=[]
	n_lines=0
	line=f.readline()
	while len(line)>0:
		n_lines+=1
		out.write(line)
		sline=line.split()
		if len(sline)==0:
			line=f.readline()
			continue
		#Check for formatting signal that header ended:
		if sline[0]=="*":
			return rods,n_lines
		if len(sline)==4 and "nulpunktsfejl" in line.lower():
			rods.append([sline[0][:-1],float(sline[-2])])
		line=f.readline()
	return None,None

def GetDiff(l1,l2):
	if len(l1)!=len(l2):
		return None
	diff=[l1-l2 for l1,l2 in zip(l1,l2)]
	return diff

def GetStats(data):
	sd=None
	n=len(data)
	if n==0:
		return None,None
	m=sum(data)/float(n)
	if n>1:
		sq_dev=sum([(x-m)**2/(n-1) for x in data])
		sd=sqrt(sq_dev)
	return m,sd
		
	
	
def Usage():
	sys.stdout=sys.__stdout__
	PROGNAME=os.path.basename(sys.argv[0])
	print("%s version: %s" %(PROGNAME,VERSION))
	print("To run:")
	print("%s <input_files> <output_dir>" %PROGNAME)
	sys.exit()

def main(args):
	if len(args)<3:
		Usage()
	files=glob.glob(args[1])
	if len(files)==0:
		print("No input files!")
		Usage()
	outdir=args[2]
	ndiffs=[]
	diffs=[]
	ndiffs2=[]
	diffs2=[]
	log_name="rodkali_log.log"
	try:
		log_file=open(log_name,"w")
	except:
		print("Could not open logfile: %s" %log_name)
		Usage()
	sys.stdout=RedirectStdout(log_file)
	if not os.path.exists(outdir):
		os.mkdir(outdir)
	for fname in files:
		out=None
		try:
			f=open(fname)
		except:
			continue
		line=f.readline()
		if "MGL" in line:
			print("Reading %s" %fname)
			base,ext=os.path.splitext(os.path.basename(fname))
			outname=os.path.join(outdir,base+"_corr"+ext)
			try:
				out=open(outname,"w")
			except:
				print("Could not open outfile %s." %outname)
				return -1
			out.write(line);
			rods,n_lines=GetRods(f,out)
			out.write("; Corrections calculated at %s\n" %time.asctime())
			out.write("; using %s, version: %s\n" %(os.path.basename(args[0]),VERSION))
			for rod,zs in rods:
				if rod in RODS:
					RODS[rod].SetZeroshift(zs)
				else:
					print("Warning: rod %s not globally defined!" %rod)
					print("Using a standard correction!")
					RODS[rod]=Rod(rod,zeroshift=zs)
			try:
				stretches,msg=GetData(f,RODS,n_lines)
			except Exception,msg:
				print(repr(msg))
				print("This is probably something serious (wrong rod, wrong zeroshift) etc. Check data!")
				print("No ouput - continuing....")
				out.close()
				continue
			if len(msg)>0:
				print msg
			print("Got %d stretches" %len(stretches))
			for s in stretches:
				bc,fc,msg,ok=s.ApplyCorrection()
				if not ok:
					print msg
				h_uncorr,h_corr=s.GetHdiff(),s.GetHdiff(bc,fc)
				diff=abs(h_corr-h_uncorr)*1e3  #convert to mm - used in all calculations on diffs below.
				ndiff=diff/sqrt(s.distance*1e-3)
				p1,p2=s.GetPoints()
				if ndiff>0.2: #0,2 ne limit for report
					mean_temp=sum(s.temp)/float(len(s.temp))
					print("Large correction!")
					print("file: %s, stretch: %s->%s, diff: %.4f mm, dist: %.2f m" %(fname,p1,p2,diff,s.distance))
					print("raw: %.6f m, corr: %.6fm" %(h_uncorr,h_corr))
					print("normalised: %.6f ne" %(ndiff))
					print("Mean-temp: %.2f deg C" %mean_temp)
				ndiffs.append(ndiff)
				diffs.append(diff)
				if True: #perhaps add some switch here for no file output....
					out.write("; %s to %s\n" %(p1,p2))
					out.write("; ")
					head=s.head
					for token in head:
						out.write(token+" ")
					head[6]="%.7f" %h_corr
					out.write("\n")
					for token in head:
						out.write(token+" ")
					out.write("\n")
			out.close()
		else:
			print("%s not (new) MGL file" %fname)
		f.close()
	if len(diffs)==0:
		print("No hdiffs found!")
		log_file.close()
		Usage()
	m_diff,sd_diff=GetStats(diffs)
	m_norm,sd_norm=GetStats(ndiffs)
	max_diff=max(map(abs,diffs))
	max_ne=max(map(abs,ndiffs))
	print("Number of hdiffs:     %d" %len(diffs))
	print("Mean (abs) diff:      %.6f mm" %m_diff)
	print("Std-dev  :            %.6f mm" %sd_diff)
	print("Max      :            %.6f mm" %max_diff)
	print("Mean normalized diff: %.6f ne" %m_norm)
	print("Std-dev  :            %.6f ne" %sd_norm)
	print("Max      :            %.6f ne" %max_ne)
	log_file.close()
	return 
	
if __name__=="__main__":
	sys.exit(main(sys.argv))
	