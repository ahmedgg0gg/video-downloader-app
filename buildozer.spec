[app]
title = Video Downloader
package.name = vdownloader
package.domain = org.test
source.dir = .
version = 1.0
requirements = python3,kivy,yt-dlp,arabic_reshaper,python-bidi
orientation = portrait
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE
android.api = 31
        
[buildozer]
log_level = 2
warn_on_root = 1
