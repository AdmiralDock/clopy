# clopy
Not-well-written python script inspired by Clop for Apple computers, but for Windows!
## How to use
The script has an icon in the system tray, right clicking it has an option to exit. The script checks clipboard constantly for PNG data and when found, saves the file, runs optipng on it and copies the resulting smaller png back to your clipboard.
## Requirements
```
pystray
six
pillow
```
and a copy of OptiPNG installed and in $PATH  
## Additional notes
You might need to set powershell local script execution policy for the copy to clipboard function to work.
