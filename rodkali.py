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
from datetime import datetime
VERSION="1.1 2012-10-25"
DEBUG=False
ND_VALUE=-999
CALIBRATION_PATH="."

	
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
	
############################
## Function which reads a calibration file - format
## Long_rod_name,l_0 [m],m_0,[ppm],alpha_T [ppm],v_G [m],T_0 [degC]  #l_0 and v_g are zero-shift constants and ARE not used now - should be zero!
## alias_name,Long_rod_name   #add a short alias name e.g: 110 ROD_53278
## Comma is used as separator!

def ReadCalibrationFile(f):
	date=None
	rods=dict()
	alias=dict()
	data=dict()
	for line in f:
		line=line.strip()
		if "#" in line:
			line=line[:line.index("#")] #remove comments
		if len(line)>0:
			items=map(lambda x:x.strip(),line.split(","))
			if len(items)>1:
				if len(items)==6:	
					long_name=items[0]
					try:
						l0,m0,alpha_t,vg,t0=map(float,items[1:])
					except:
						print("Wrong format of rod specification: %s" %line)
					else:
						data[long_name]=[l0,m0,alpha_t,vg,t0]
						print("Defined rod %s" %long_name)
				elif len(items)==2:
					short_name=items[0]
					long_name=items[1]
					alias[short_name]=long_name
					print("Added alias: %s=%s" %(short_name,long_name))
				else:
					print("Unintepretable line: %s" %line)
					
			else:
				print("Bad line: %s" %line)
	for short_name in alias:
		long_name=alias[short_name]
		if long_name in data:
			rods[short_name]=Rod(short_name,data[long_name])
		else:
			print("Bad alias for %s, rod %s not defined!" %(short_name,long_name))
	return rods

def FindRCF(date):
	#find the newest calibration file which is older than the date#
	print("Finding matching rod calibration file (rcf)....")
	fnames=glob.glob(os.path.join(CALIBRATION_PATH,"*.rcf"))
	best_date=datetime(1900,1,1)
	rcf_name=None
	for fname in fnames:
		try:
			y,m,d=map(int,os.path.splitext(os.path.basename(fname))[0].split("_"))
		except:
			print("Bad name format of rcf: %s" %os.path.basename(fname))
		else:
			file_date=datetime(y,m,d)
			if (file_date<date and file_date>best_date):
				best_date=file_date
				rcf_name=fname
	return rcf_name
		

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
# Gets rods, and date, from data-file and copies header to output#
################################

	
def ReadHeader(f,out):
	rods=[]
	n_lines=0
	dato=None
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
			return rods,n_lines,dato
		if len(sline)==4 and "nulpunktsfejl" in line.lower():
			rods.append([sline[0][:-1],float(sline[-2])])
		elif "Dato" in line:
			d,m,y=map(int,sline[-2].split("."))
			dato=datetime(y,m,d)
		line=f.readline()
	return None,None,None

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
	print("%s <input_files> <output_dir> <calibration_file_path> (last arg optional)" %PROGNAME)
	sys.exit()

def main(args):
	if len(args)<3:
		Usage()
	files=glob.glob(args[1])
	if len(files)==0:
		print("No input files!")
		Usage()
	outdir=args[2]
	#We can specify a rod calibration file - rcf- to use manually#
	if len(args)>3:
		input_rcf=args[3]
		try:
			f=open(input_rcf)
		except:
			print("Unable to open rod calibration file %s" %input_rcf)
			Usage()
		RODS=ReadCalibrationFile(f)
		f.close()
		if len(RODS)==0:
			print("No rods defined in calibration file %s" &input_rcf)
			Usage()
	else:
		input_rcf=None
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
			rods,n_lines,date=ReadHeader(f,out)
			if date is None:
				print("Unable to read date from header!")
				if input_rcf is None:
					print("Fix header or specify a calibration file manually - skipping.")
					out.close()
					f.close()
					continue
			
			if input_rcf is None:
				name_rcf=FindRCF(date)
				if name_rcf is None:
					print("Found no matching rod calibration file! - skipping!")
					out.close()
					f.close()
					continue
				g=open(name_rcf)
				RODS=ReadCalibrationFile(g)
				g.close()
				if len(RODS)==0:
					print("No rods defined in %s ! - skipping..." %name_rcf)
					out.close()
					f.close()
					continue
				
			else:
				name_rcf=input_rcf
			print("Using rod calibration file: %s" %name_rcf)
			if date is not None:
				print("Date of data file is: %s" %(date.isoformat()[:10]))
			out.write("; Corrections calculated at %s\n" %time.asctime())
			out.write("; using %s, version: %s\n" %(os.path.basename(args[0]),VERSION))
			out.write("; using correction file: %s\n" %name_rcf)
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
	