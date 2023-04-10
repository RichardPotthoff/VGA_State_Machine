from PIL import Image
import numpy as np
from matplotlib import pyplot as plt
from collections import deque
from time import perf_counter
t0=perf_counter()
def timer():
  return perf_counter()-t0
     
def GrayToBinary32(num):
    num ^= num >> 16
    num ^= num >>  8
    num ^= num >>  4
    num ^= num >>  2
    num ^= num >>  1
    return num   

def Binary32ToGray(num):
  return num^(num>>1)
  
def shift_bits(i,delta):
  if delta<0:
    return i>>-delta
  else:
    return i<<delta
    
def bit_count(n):
  n = (n & 0x5555555555555555) + ((n & 0xAAAAAAAAAAAAAAAA) >> 1)
  n = (n & 0x3333333333333333) + ((n & 0xCCCCCCCCCCCCCCCC) >> 2)
  n = (n & 0x0F0F0F0F0F0F0F0F) + ((n & 0xF0F0F0F0F0F0F0F0) >> 4)
  n = (n & 0x00FF00FF00FF00FF) + ((n & 0xFF00FF00FF00FF00) >> 8)
  n = (n & 0x0000FFFF0000FFFF) + ((n & 0xFFFF0000FFFF0000) >> 16)
  n = (n & 0x00000000FFFFFFFF) + ((n & 0xFFFFFFFF00000000) >> 32) # This last & isn't strictly necessary.
  return n
  
def swap_bits(i,bitpos1,bitpos2):
  b1=i&(1<<bitpos1)
  b2=i&(1<<bitpos2)
  return i^b1^b2^shift_bits(b1,bitpos2-bitpos1)^shift_bits(b2,bitpos1-bitpos2)
  
def graySequenceGen(gstart,gend,n):
  if n%2==1: raise Exception(f'graySequenceGen(gstart={gstart},gend={gend},n={n}): n must be even!')
  msb=(n-1).bit_length()
  bit_diff=gstart^gend 
  if bit_count(bit_diff)!=1:raise Exception(f'graySequenceGen(gstart={gstart},gend={gend},n={n}): gstart and gend must have differ in exactly one bit position!')
  bit_diff_pos=bit_diff.bit_length()-1
  m=1<<(msb+1)
  istart=(m-n)//2
  mask=swap_bits(istart^(istart>>1),msb,bit_diff_pos)^gstart
  for i in range(istart,istart+n):
#    print(locals())
    yield swap_bits(i^(i>>1),msb,bit_diff_pos)^mask

def grayVGA(width=640,height=480,hblank=800-640,vblank=525-480):
  '''
  Produce a cyclic sequence of gray-codes 
  '''
  blankmask=1<<(width*height).bit_length()#one bit-position above the used video address space
  usedStates=set()
  addr=0
  for y in range(height):
    for x in range(width):
      g=Binary32ToGray(addr)
      usedStates.add(g)
      yield g
      addr+=1
    for g in graySequenceGen(blankmask|Binary32ToGray(addr-1),blankmask|Binary32ToGray(addr),hblank):
      usedStates.add(g)
      yield g
  lastState=g
  vblankStart=g
  k=0
  for g in graySequenceGen(blankmask|Binary32ToGray(addr),blankmask|Binary32ToGray(addr)^128,vblank*2*800):
    if (not g in usedStates) and bit_count(g^lastState)==1:
      usedStates.add(g)
      yield g
      lastState=g
      k+=1
      if k>=vblank*800-6:#stop 6 steps short of end of sequence
        break
  for i in (5,2,17,10,18,7,):#manually clear the last 6 bits to close the cycle
    g^=1<<i
    yield g
  
mask=480*640//2    
print(f'before call off grayVGA: {timer()}')
#
state_cycle=np.array([k^mask for k in grayVGA()],dtype=np.uint32)
print(f'after call off grayVGA: {timer()}')


rom=np.zeros(1<<20,dtype=np.uint32)
#have all rom addresses point to the next state in the cycle (roll(-1))
rom[state_cycle&((1<<20)-1)]=np.roll(state_cycle,-1)

vsyncStart=state_cycle[480*800]#end of last visible scan line
usedStates=set(state_cycle) 

#collect all unused states, and route them to the 'vsyncStart'-state
resetState=deque((vsyncStart,))
resetState_=deque()
print(f'before reset state: {timer()}')
if True:
 n=0
 while resetState:
#  if n<=0: break
  n-=1
  g=resetState.popleft()
  mask=1<<19
  while mask:
    g_=g^mask
    if not (g_ in usedStates):
      rom[g_]=g
      usedStates.add(g_)
      if g_&(1<<19)!=0:
        resetState.append(g_)
      else:
        resetState_.append(g_)
    mask>>=1
  if len(resetState)==0:
    resetState=resetState_

#all states should now be defined, and point to the next state in the chain:
#either to the next state in the cycle, or towards 'vsyncStart' (for the unused states)
#check for the whole ROM, that the address and stored value are different in exactly one bit position
bitchanges=[bit_count(int(val&((1<<20)-1))^addr) for addr,val in enumerate(rom)]
assert min(bitchanges)==1
assert max(bitchanges)==1
    

print(f'after reset state: {timer()}')

def b332toRGB(b332):
  deltaRG=255/7
  deltaB=255/3
  return (int(((b332>>5)&7)*deltaRG+0.5),int(((b332>>2)&7)*deltaRG+0.5),int((b332&3)*deltaB+0.5))
with open('Starman.332','rb') as f: 
  Starman332=f.read()
Starman332g=[0]*640*480
for k,pixel332 in enumerate(Starman332):
  g=k^(k>>1)^(640*480//2)
  Starman332g[g]=pixel332
  
i=480*640//2
for k in range(525*800):
  k1=(k+1)%(525*800)
  y=k1//800
  x=k1%800
  if (  x in range(0,640)) and (y in range(0,480)) :
    rom[i]|=Starman332[y*640+x]<<24#image
    rom[i]|=1<<20 #valid address
  if x in  range(700,740)  :rom[i]|=1<<21 #hsync
  if y in  range(500,505)  :rom[i]|=1<<22 #vsync
  if ( bit_count(i)&1)==1  :rom[i]|=1<<23 #clock 
  i=int(rom[i])&((1<<20)-1)
print(f'after adding sync info: {timer()}')

def romSequence(rom=rom,start_addr=0,addr_mask=None,max_iter=None):
  if addr_mask==None: addr_mask=(1<<((len(rom)-1).bit_length()))-1
  if max_iter==None:  max_iter=2*len(rom) # ensures full cycle for ramdom start address
  addr=start_addr
  while max_iter!=0:
    yield addr
    addr=rom[addr&addr_mask]
    max_iter-=1
    if max_iter<0: max_iter=-1#prevent negative overflow

def copyToVideoRAM(data,VideoRAM=None):
  if VideoRAM==None:
    VideoRAM=[None]*len(data)
  data_length=len(VideoRAM)
  mask=data_length>>1
  for k,pixel in enumerate(data):
    if k>=data_length:
      break
    g=k^(k>>1)^mask #video address in gray-code
    VideoRAM[g]=pixel
  return VideoRAM
  
VideoRAM=[None]*640*480  
copyToVideoRAM(Starman332,VideoRAM)#copy video data in gray-code order

frame1=Image.new('RGB',(800,525))
old_hsync=False
old_vsync=False
x=y=vsync_count=0
print(f'before receiving romSequence: {timer()}')

for data_output in romSequence(rom,start_addr=vsyncStart):
  if vsync_count>=2: 
    break
  blank=(data_output&(1<<19))!=0
  addr_valid=(data_output&(1<<20))!=0
  hsync=(data_output&(1<<21))!=0
  vsync=(data_output&(1<<22))!=0
  clk=(data_output&(1<<23))!=0
  addr=data_output&((1<<20)-1)#20-bit address
  if old_hsync and not hsync:
    x=0
    y+=1
    y=min(y,524)
  else:
    x+=1
    x=min(x,799)
  if old_vsync and not vsync:
    vsync_count+=1
    y=0
  if vsync_count>=1:
    if addr_valid:
      pixel=b332toRGB(VideoRAM[addr])#read byte from gray-ordered array, convert to RGB
#      pixel=b332toRGB(data_output>>24)#use bit 24 to 31 as pixel data, convert to RGB
      pass
    else:
      pixel=(255 if hsync else 0,255 if vsync else 0,255 if clk else 0)  
    frame1.putpixel((x,y),pixel)
  old_hsync,old_vsync=hsync,vsync 

print(f'after receiving romSequence: {timer()}')
 
img1g=Image.new('RGB',(640,480))
img1g.putdata([b332toRGB(b332) for b332 in VideoRAM])#scrambled because of gray-code ordering
print('Video RAM content (scrambled because of gray-code ordering):')
img1g.show()
print('Video output (generated by the gray-code based state machine):')
frame1.show()#unscrambled because the state machine produces sequence of gray-codes

#(rom&((1<<16)-1)).astype(np.uint16).tofile('rom_lower.bin')
#(rom>>16).astype(np.uint16).tofile('rom_upper.bin')
#rom2=(np.fromfile('rom_upper.bin',dtype=np.uint16).astype(np.uint32)<<16)|np.fromfile('rom_lower.bin',dtype=np.uint16)


