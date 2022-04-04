from socket import *
import os
import sys
import struct
import time
import select
import binascii
import statistics
# Should use stdev

ICMP_ECHO_REQUEST = 8


def checksum(string):
  csum = 0
  countTo = (len(string) // 2) * 2
  count = 0

  while count < countTo:
    thisVal = (string[count + 1]) * 256 + (string[count])
    csum += thisVal
    csum &= 0xffffffff
    count += 2

  if countTo < len(string):
    csum += (string[len(string) - 1])
    csum &= 0xffffffff

  csum = (csum >> 16) + (csum & 0xffff)
  csum = csum + (csum >> 16)
  answer = ~csum
  answer = answer & 0xffff
  answer = answer >> 8 | (answer << 8 & 0xff00)
  return answer



def receiveOnePing(mySocket, ID, timeout, destAddr):
  timeLeft = timeout

  while 1:
    startedSelect = time.time()
    whatReady = select.select([mySocket], [], [], timeLeft)
    howLongInSelect = (time.time() - startedSelect)
    if whatReady[0] == []:  # Timeout
      print("Request timed out.")
      return None

    timeReceived = time.time()
    recPacket, addr = mySocket.recvfrom(1024)

    # Fill in start

    # Fetch the ICMP header from the IP packet
    # IP header is 20 bytes. ICMP header starts after the IP header. ICMP header is 8 bytes.
    # ICMP header is type (8), code (8), checksum (16), id (16), sequence (16)
    icmp_header = recPacket[20:28]
    icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_sequence = struct.unpack('bbHHh', icmp_header)

    ip_header = recPacket[0:20]
    ip_ttl = ip_header[8:9]
    (ttl,) = struct.unpack('B', ip_ttl)

    # ICMP echo response payload starts after the ICMP header.
    data = recPacket[28:]

    # Data contains the time when echo request was sent.
    (timeSent,) = struct.unpack("d", data)

    # If the packet ID of the response matches that of the request,
    # we have received a reply to our ping.
    if icmp_id == ID:
      delay = (timeReceived - timeSent) * 1000
      print("Reply from {}: bytes={} time={}ms TTL={}".format(addr[0], len(data), round(delay, 7), ttl))
      return delay

    # Fill in end
    timeLeft = timeLeft - howLongInSelect
    if timeLeft <= 0:
      print("Request timed out.")
      return None


def sendOnePing(mySocket, destAddr, ID):
  # Header is type (8), code (8), checksum (16), id (16), sequence (16)

  myChecksum = 0
  # Make a dummy header with a 0 checksum
  # struct -- Interpret strings as packed binary data
  header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
  data = struct.pack("d", time.time())
  # Calculate the checksum on the data and the dummy header.
  myChecksum = checksum(header + data)

  # Get the right checksum, and put in the header

  if sys.platform == 'darwin':
    # Convert 16-bit integers from host to network  byte order
    myChecksum = htons(myChecksum) & 0xffff
  else:
    myChecksum = htons(myChecksum)


  header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
  packet = header + data

  mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str


  # Both LISTS and TUPLES consist of a number of objects
  # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
  icmp = getprotobyname("icmp")


  # SOCK_RAW is a powerful socket type. For more details:   https://sock-raw.org/papers/sock_raw
  mySocket = socket(AF_INET, SOCK_RAW, icmp)

  myID = os.getpid() & 0xFFFF  # Return the current process i
  sendOnePing(mySocket, destAddr, myID)
  delay = receiveOnePing(mySocket, myID, timeout, destAddr)
  mySocket.close()
  return delay


def ping(host, timeout=1):
  # timeout=1 means: If one second goes by without a reply from the server,   
  # the client assumes that either the client's ping or the server's pong is lost
  try:
    dest = gethostbyname(host)
  except:
    print("cannot resolve {}: Unknown host".format(host))
    return ["0", "0.0", "0", "0.0"]

  print("Pinging " + dest + " using Python:")
  print("")
  
  #Send ping requests to a server separated by approximately one second
  #Add something here to collect the delays of each ping in a list so you can calculate vars after your ping
  delays = []
  for i in range(0,4): #Four pings will be sent (loop runs for i=0, 1, 2, 3)
    delay = doOnePing(dest, timeout)
    if delay is not None:
      delays.append(delay)
    time.sleep(1)  # one second

  #You should have the values of delay for each ping here; fill in calculation for packet_min, packet_avg, packet_max, and stdev
  if len(delays) == 0:
    packet_min = 0
    packet_max = 0
    packet_avg = 0
    stdev_var = 0
  else:
    packet_min = min(delays)
    packet_max = max(delays)
    packet_avg = sum(delays) / len(delays)
    stdev_var = statistics.stdev(delays)
    #Alternate method of calculating a standard deviation without using the statistics package
    #stdev_var = math.sqrt(sum((delay - packet_avg)**2 for delay in delays) / len(delays))
  vars = [str(round(packet_min, 8)), str(round(packet_avg, 8)), str(round(packet_max, 8)),str(round(stdev_var, 8))]

  print("")
  print("--- {} ping statistics ---".format(host))
  print("4 packets transmitted, {} packets received, {}% packet loss".format(len(delays), round((4.0-len(delays))/4.0*100, 1)))
  if len(delays) > 0:
    print("round-trip min/avg/max/stddev = {}/{}/{}/{} ms".format(round(packet_min, 2), round(packet_avg, 2), round(packet_max, 2), round(stdev_var, 2)))
  else:
    print("round-trip min/avg/max/stddev = 0/0.0/0/0.0 ms")

  return vars

if __name__ == '__main__':
  if len(sys.argv) == 2:
    ping(sys.argv[1])
  else:
    ping("google.co.il")
