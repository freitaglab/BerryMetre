$port = 6819
$targetPort = 6819
$endpoint = New-Object System.Net.IPEndPoint ([IPAddress]::Any, $port)

# Script can be used as a simple relay to multiplex UDP packages to another receiver. Change this accordingly
$targetIP = "192.168.15.99" 

function Get-TimeStamp {
    
    return "[{0:MM/dd/yy} {0:HH:mm:ss}]" -f (Get-Date)
    
}

function Send-UdpDatagram
{
      Param ([string] $EndPoint, 
      [int] $Port, 
      [string] $Message)

      # Write-Host "Send datagram..."
      Write-Host "$(Get-TimeStamp) $Message"

      $IP = [System.Net.Dns]::GetHostAddresses($EndPoint) 
      $Address = [System.Net.IPAddress]::Parse($IP) 
      $EndPoints = New-Object System.Net.IPEndPoint($Address, $Port) 
      $Socket = New-Object System.Net.Sockets.UDPClient 
      $EncodedText = [Text.Encoding]::ASCII.GetBytes($Message) 
      $SendMessage = $Socket.Send($EncodedText, $EncodedText.Length, $EndPoints) 
      $Socket.Close() 
} 


Write-Host "Starting..."
Send-UdpDatagram -EndPoint $targetIP -Port $targetPort -Message "Hello from Relay!"
Write-Host "Done..."

Try {
    while($true) {
        $socket = New-Object System.Net.Sockets.UdpClient $port
        $content = $socket.Receive([ref]$endpoint)
        $socket.Close()
        $forwardMsg = [Text.Encoding]::ASCII.GetString($content)
        Send-UdpDatagram -EndPoint $targetIP -Port $targetPort -Message $forwardMsg
    }
} Catch {
    "$($Error[0])"
}