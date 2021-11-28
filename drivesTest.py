# ---SETTINGS---

#Size of block files to write in bytes. Must be multiples of 10. Higher values might result in faster speed but more memory consumption. Default: 100_000_000 bytes
BLOCK_SIZE = 100_000_000 #bytes
#Size to subtract * blocks from total disk space. Writing bytes to disk uses extra disk space depending on filesystem. Values too low will cause the disk to run out of space. Default: 20_000 bytes.
BLOCK_SIZE_BIAS = 20_000 #bytes

# ---END OF SETTINGS---

#import
from sys import argv
from shutil import disk_usage
from multiprocessing import Process, Queue
#main function
def processFunc(driveLetter, procMsg):
	#init
	dataLoop='0123456789'
	mainData = {}
	blocks = {}
	test = True
	mainData['fullBlockData'] = dataLoop * (BLOCK_SIZE // 10)
	mainData['fullBlockHash'] = hash(mainData['fullBlockData'])

	#analyze disk
	total, used, free = disk_usage(driveLetter+":/")
	mainData['fullBlockCount'] = free // BLOCK_SIZE #create blocks
	mainData['finalBlockSize'] = (free - (BLOCK_SIZE_BIAS * (mainData['fullBlockCount'] + 1))) - (mainData['fullBlockCount'] * BLOCK_SIZE)

	#write full blocks
	procMsg.put([driveLetter,'writing','0/'+str(mainData['fullBlockCount']+1),'pending'])
	for i in range(mainData['fullBlockCount']):
		with open(driveLetter+":/drivesTest"+str(i)+".block", "wt") as file:
			file.write(mainData['fullBlockData'])
		procMsg.put([driveLetter,'writing',str(i+1)+'/'+str(mainData['fullBlockCount']+1),'pending'])
	mainData['fullBlockData'] = '' #take data off memory once finished
	
	#write final block
	mainData['finalBlockData'] = dataLoop * (mainData['finalBlockSize'] // 10)
	for i in range(mainData['finalBlockSize'] - ((mainData['finalBlockSize'] // 10)*10)):
		mainData['finalBlockData'] += dataLoop[i]
	mainData['finalBlockHash'] = hash(mainData['finalBlockData'])
	with open(driveLetter+":/drivesTest"+str(mainData['fullBlockCount'])+".block", "wt") as file:
		file.write(mainData['finalBlockData'])
	procMsg.put([driveLetter,'writing',str(mainData['fullBlockCount']+1)+'/'+str(mainData['fullBlockCount']+1),'pending'])
	mainData['finalBLockData'] = '' #take data off memory once finished

	#hash
	for i in range(mainData['fullBlockCount']+1):
		try:
			with open(driveLetter+":/drivesTest"+str(i)+".block", "rt") as file:
				blocks['hashBlock'+str(i)] = hash(file.read())
		except OSError:
			test = False
		procMsg.put([driveLetter,'reading',str(i+1)+'/'+str(mainData['fullBlockCount']+1),'pending'])
	for i in range(mainData['fullBlockCount']):
		if blocks['hashBlock'+str(i)] != mainData['fullBlockHash']:
			test = False
	if mainData['finalBlockHash'] != blocks['hashBlock'+str(mainData['fullBlockCount'])]:
		test = False

	#conclude
	if test:
		procMsg.put([driveLetter,'finished',str(mainData['fullBlockCount']+1)+'/'+str(mainData['fullBlockCount']+1),'PASSED'])
	else:
		procMsg.put([driveLetter,'finished',str(mainData['fullBlockCount']+1)+'/'+str(mainData['fullBlockCount']+1),'FAILED'])

#start
if __name__ == "__main__":
	#gather input
	if len(argv) > 2:
		osType = argv[1]
		drivesToScan = []
		for i in range(2, len(argv)):
			drivesToScan.append(argv[i])
	else:
		osType = input('Enter OS "windows" or "linux":')
		if osType != 'windows':
			print('Tool currently only supports windows. Aborting.')
			exit(0)
		drivesToScan = input('Drives to scan seperated by commas (E,F,G,etc.):').split(',')
	print("Make sure all selected drives are empty for best results. This will not delete existing files.")
	#show drive stats
	for x in drivesToScan:
		total, used, free = disk_usage(x+":/")
		print(f"{x}:/ used:{used},free:{free},total:{total}.")
	if len(argv) <= 2:
		permission = input('Above looks OK? Continue test? (y/N):')
		if permission != 'y':
			print('Aborting.')
			exit(0)
	#spawn processes
	processes = []
	stats = {}
	procMsg = Queue()
	for drive in drivesToScan:
		stats[drive+'state'] = 'starting'
		stats[drive+'progress'] = '*/*'
		stats[drive+'success'] = 'pending'
		process = Process(target=processFunc, args=(drive, procMsg))
		processes.append(process)
		process.start()

	#stats.
	print('')
	while True:
		#test when to break
		keepLooping = False
		statusMsg = ''
		for drive in drivesToScan:
			if stats[drive+'state'] != 'finished':
				keepLooping = True
		if not keepLooping:
			break
		#get stats
		incMsg = procMsg.get()
		stats[incMsg[0]+'state'] = incMsg[1]
		stats[incMsg[0]+'progress'] = incMsg[2]
		stats[incMsg[0]+'success'] = incMsg[3]
		#print stats
		for drive in drivesToScan:
			statusMsg += f'{drive}: {stats[drive+"state"]} {stats[drive+"progress"]} {stats[drive+"success"]} .'
		print(statusMsg, end="\r")
	print('')
	#finish
	for process in processes:
		process.join()
	print('Finished.')
	if len(argv) <= 2: #keep console open if program was run without arguments
		input('')