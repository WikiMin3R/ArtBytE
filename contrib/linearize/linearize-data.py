#!/usr/bin/python
#
# linearize-data.py: Construct a linear, no-fork version of the chain.
#
# Copyright (c) 2013 The Bitcoin developers
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

import json
import struct
import re
import os
import base64
import httplib
import sys
import hashlib
import datetime
import time
import ltc_scrypt

settings = {}


def uint32(x):
	return x & 0xffffffffL

def bytereverse(x):
	return uint32(( ((x) << 24) | (((x) << 8) & 0x00ff0000) |
		       (((x) >> 8) & 0x0000ff00) | ((x) >> 24) ))

def bufreverse(in_buf):
	out_words = []
	for i in range(0, len(in_buf), 4):
		word = struct.unpack('@I', in_buf[i:i+4])[0]
		out_words.append(struct.pack('@I', bytereverse(word)))
	return ''.join(out_words)

def wordreverse(in_buf):
	out_words = []
	for i in range(0, len(in_buf), 4):
		out_words.append(in_buf[i:i+4])
	out_words.reverse()
	return ''.join(out_words)

def calc_hdr_hash(aby_hdr):
	hash1 = hashlib.sha256()
	hash1.update(aby_hdr)
	hash1_o = hash1.digest()

	hash2 = hashlib.sha256()
	hash2.update(hash1_o)
	hash2_o = hash2.digest()

	return hash2_o

def calc_hash_str(aby_hdr):
	hash = calc_hdr_hash(aby_hdr)
	hash = bufreverse(hash)
	hash = wordreverse(hash)
	hash_str = hash.encode('hex')
	return hash_str

def calc_scrypt_hash_str(aby_hdr):
	hash = ltc_scrypt.getPoWHash(aby_hdr)
	hash = bufreverse(hash)
	hash = wordreverse(hash)
	hash_str = hash.encode('hex')
	return hash_str

def get_aby_dt(aby_hdr):
	members = struct.unpack("<I", aby_hdr[68:68+4])
	nTime = members[0]
	dt = datetime.datetime.fromtimestamp(nTime)
	dt_ym = datetime.datetime(dt.year, dt.month, 1)
	return (dt_ym, nTime)

def get_block_hashes(settings):
	abyindex = []
	f = open(settings['hashlist'], "r")
	for line in f:
		line = line.rstrip()
		abyindex.append(line)

	print("Read " + str(len(abyindex)) + " hashes")

	return abyindex

def mkblockset(abyindex):
	abymap = {}
	for hash in abyindex:
		abymap[hash] = True
	return abymap

def copydata(settings, abyindex, abyset):
	inFn = 1
	inF = None
	outFn = 0
	outsz = 0
	outF = None
	outFname = None
	abyCount = 0

	lastDate = datetime.datetime(2000, 1, 1)
	highTS = 1408893517 - 315360000
	timestampSplit = False
	fileOutput = True
	setFileTime = False
	maxOutSz = settings['max_out_sz']
	if 'output' in settings:
		fileOutput = False
	if settings['file_timestamp'] != 0:
		setFileTime = True
	if settings['split_timestamp'] != 0:
		timestampSplit = True

	while True:
		if not inF:
			fname = "%s/aby%04d.dat" % (settings['input'], inFn)
			print("Input file" + fname)
			try:
				inF = open(fname, "rb")
			except IOError:
				print "Done"
				return

		inhdr = inF.read(8)
		if (not inhdr or (inhdr[0] == "\0")):
			inF.close()
			inF = None
			inFn = inFn + 1
			continue

		inMagic = inhdr[:4]
		if (inMagic != settings['netmagic']):
			print("Invalid magic:" + inMagic)
			return
		inLenLE = inhdr[4:]
		su = struct.unpack("<I", inLenLE)
		inLen = su[0]
		rawblock = inF.read(inLen)
		aby_hdr = rawblock[:80]

		hash_str = 0
		if abyCount > 999319000:
			hash_str = calc_hash_str(aby_hdr)
		else:
			hash_str = calc_scrypt_hash_str(aby_hdr)

		if not hash_str in abyset:
			print("Skipping unknown block " + hash_str)
			continue

		if abyindex[abyCount] != hash_str:
			print("Out of order block.")
			print("Expected " + abyindex[abyCount])
			print("Got " + hash_str)
			sys.exit(1)

		if not fileOutput and ((outsz + inLen) > maxOutSz):
			outF.close()
			if setFileTime:
				os.utime(outFname, (int(time.time()), highTS))
			outF = None
			outFname = None
			outFn = outFn + 1
			outsz = 0

		(abyDate, abyTS) = get_aby_dt(aby_hdr)
		if timestampSplit and (abyDate > lastDate):
			print("New month " + abyDate.strftime("%Y-%m") + " @ " + hash_str)
			lastDate = abyDate
			if outF:
				outF.close()
				if setFileTime:
					os.utime(outFname, (int(time.time()), highTS))
				outF = None
				outFname = None
				outFn = outFn + 1
				outsz = 0

		if not outF:
			if fileOutput:
				outFname = settings['output_file']
			else:
				outFname = "%s/aby%05d.dat" % (settings['output'], outFn)
			print("Output file" + outFname)
			outF = open(outFname, "wb")

		outF.write(inhdr)
		outF.write(rawblock)
		outsz = outsz + inLen + 8

		abyCount = abyCount + 1
		if abyTS > highTS:
			highTS = abyTS

		if (abyCount % 1000) == 0:
			print("Wrote " + str(abyCount) + " blocks")

if __name__ == '__main__':
	if len(sys.argv) != 2:
		print "Usage: linearize-data.py CONFIG-FILE"
		sys.exit(1)

	f = open(sys.argv[1])
	for line in f:
		# skip comment lines
		m = re.search('^\s*#', line)
		if m:
			continue

		# parse key=value lines
		m = re.search('^(\w+)\s*=\s*(\S.*)$', line)
		if m is None:
			continue
		settings[m.group(1)] = m.group(2)
	f.close()

	if 'netmagic' not in settings:
		settings['netmagic'] = '70352205'
	if 'input' not in settings:
		settings['input'] = 'input'
	if 'hashlist' not in settings:
		settings['hashlist'] = 'hashlist.txt'
	if 'file_timestamp' not in settings:
		settings['file_timestamp'] = 0
	if 'split_timestamp' not in settings:
		settings['split_timestamp'] = 0
	if 'max_out_sz' not in settings:
		settings['max_out_sz'] = 1000L * 1000 * 1000

	settings['max_out_sz'] = long(settings['max_out_sz'])
	settings['split_timestamp'] = int(settings['split_timestamp'])
	settings['file_timestamp'] = int(settings['file_timestamp'])
	settings['netmagic'] = settings['netmagic'].decode('hex')

	if 'output_file' not in settings and 'output' not in settings:
		print("Missing output file / directory")
		sys.exit(1)

	abyindex = get_block_hashes(settings)
	abyset = mkblockset(abyindex)

	if not "000001faef25dec4fbcf906e6242621df2c183bf232f263d0ba5b101911e4563" in abyset:
		print("not found")
	else:
		copydata(settings, abyindex, abyset)


