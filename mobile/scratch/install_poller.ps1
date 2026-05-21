$deviceId = "RZ8RC1RXH6N"
$apkPath = "app/build/outputs/apk/debug/app-debug.apk"
Write-Output "Starting installation poller for 60 seconds..."
$timeout = 60
$elapsed = 0
while ($elapsed -lt $timeout) {
    $status = adb devices | Select-String -Pattern "$deviceId\s+(\w+)"
    if ($status) {
        $state = $status.Matches.Groups[1].Value
        Write-Output "Device state: $state"
        if ($state -eq "device") {
            Write-Output "Device authorized! Installing APK..."
            $res = adb -s $deviceId install -r $apkPath
            Write-Output $res
            Write-Output "SUCCESS"
            exit 0
        }
    }
    Start-Sleep -Seconds 3
    $elapsed += 3
}
Write-Output "Timeout: Device was not authorized."
exit 1
