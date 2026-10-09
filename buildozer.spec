[app]
title = Space Dodger
package.name = spacedodger
package.domain = org.spacedodger

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = tests, bin, .github, __pycache__, .buildozer

version = 1.0.0
requirements = python3,kivy

orientation = portrait
fullscreen = 1

icon.filename = %(source.dir)s/data/icon.png
presplash.filename = %(source.dir)s/data/presplash.png
presplash.color = #0A0A0E

# --- Android ---------------------------------------------------------
# No special permissions needed (high score is stored in the app sandbox).
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
# API level / NDK: intentionally left at Buildozer's tested defaults.

[buildozer]
log_level = 2
warn_on_root = 1
