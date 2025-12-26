# Phase 2 Manual Testing Guide

## Setup

1. **Open PowerShell in the WinPacMan directory**
2. **Activate the environment:**
   ```powershell
   .\winpacman_env_windows\Scripts\Activate.ps1
   ```
3. **Launch the GUI:**
   ```powershell
   python gui_pyqt6.py
   ```

---

## Test Sequence

### Test 1: Window Display Check (30 seconds)

**What to verify:**
- [ ] Window opens with modern Fluent Design styling
- [ ] Side navigation panel visible on left
- [ ] "Packages" tab active and highlighted
- [ ] Top control panel shows:
  - "Package Manager:" label
  - Dropdown with "WinGet" selected
  - Refresh button (enabled)
  - Search button (disabled/grayed out)
  - Install button (disabled/grayed out)
  - Uninstall button (disabled/grayed out)
- [ ] Main area shows empty table with headers:
  - Package Name | Version | Manager | Description
- [ ] Bottom status bar shows:
  - "Ready" or "Selected: WinGet" on left
  - No progress bar visible

**✅ PASS** if all elements are visible and properly styled
**❌ FAIL** if any element is missing or looks broken

---

### Test 2: WinGet Package Listing (1-2 minutes)

**Steps:**
1. Ensure "WinGet" is selected in dropdown
2. Click the **Refresh** button
3. Watch for progress updates
4. Wait for completion

**What to verify:**
- [ ] Progress bar appears at bottom right
- [ ] Status message changes (e.g., "Refreshing packages from winget...")
- [ ] Progress bar animates from 0% to 100%
- [ ] Window remains responsive (you can move it)
- [ ] Packages appear in table
- [ ] **All rows have LIGHT GREEN background** (#E8F5E8)
- [ ] Success notification appears (toast at top): "Success - Loaded X packages"
- [ ] Status shows "Ready"
- [ ] Progress bar disappears
- [ ] Refresh button re-enables

**Sample packages you might see:** Microsoft.PowerShell, Git.Git, Python.Python.3.12, etc.

**✅ PASS** if packages load with green rows and no errors
**❌ FAIL** if error occurs, wrong colors, or UI freezes

---

### Test 3: Chocolatey Package Listing (1-2 minutes)

**Steps:**
1. Click dropdown, select **"Chocolatey"**
2. Table should clear
3. Status should show "Selected: Chocolatey"
4. Click **Refresh** button
5. Wait for completion

**What to verify:**
- [ ] Previous WinGet packages cleared
- [ ] Progress bar appears and updates
- [ ] Chocolatey packages load
- [ ] **All rows have LIGHT ORANGE background** (#FFF4E6)
- [ ] Success notification appears
- [ ] Package count is different from WinGet

**✅ PASS** if packages load with orange rows
**❌ FAIL** if error or wrong colors

---

### Test 4: Pip Package Listing (1-2 minutes)

**Steps:**
1. Select **"Pip"** from dropdown
2. Click **Refresh**
3. Wait for completion

**What to verify:**
- [ ] Previous packages cleared
- [ ] Pip packages load
- [ ] **All rows have LIGHT BLUE background** (#E6F3FF)
- [ ] Success notification appears
- [ ] Packages like PyQt6, requests, packaging appear

**✅ PASS** if packages load with blue rows
**❌ FAIL** if error or wrong colors

---

### Test 5: NPM Package Listing (1-2 minutes)

**Steps:**
1. Select **"NPM"** from dropdown
2. Click **Refresh**
3. Wait for completion

**What to verify:**
- [ ] Previous packages cleared
- [ ] NPM global packages load
- [ ] **All rows have LIGHT PINK background** (#FCE6F3)
- [ ] Success notification appears
- [ ] Usually fewer packages than other managers

**✅ PASS** if packages load with pink rows
**❌ FAIL** if error or wrong colors

---

### Test 6: Column Sorting (30 seconds)

**Steps:**
1. Ensure packages are loaded (any manager)
2. Click **"Package Name"** header
3. Click it again

**What to verify:**
- [ ] First click: packages sort alphabetically A→Z
- [ ] Second click: packages sort reverse Z→A
- [ ] Click "Version" header → sorts by version
- [ ] Click "Manager" header → sorts by manager name
- [ ] Sorting is instant (no delay)

**✅ PASS** if all columns sort correctly
**❌ FAIL** if sorting doesn't work or is slow

---

### Test 7: Package Details Dialog (30 seconds)

**Steps:**
1. **Double-click** any package in the table
2. Read the dialog

**What to verify:**
- [ ] Dialog box appears with title "Package Details"
- [ ] Shows:
  - Name: [package name]
  - Version: [version number]
  - Manager: [winget/choco/pip/npm]
  - Description: [description or N/A]
- [ ] Click OK to close
- [ ] Dialog closes cleanly

**✅ PASS** if dialog shows correct info
**❌ FAIL** if dialog doesn't appear or shows wrong info

---

### Test 8: UI Responsiveness During Operation (1 minute)

**Steps:**
1. Select WinGet
2. Click Refresh
3. **Immediately while loading:**
   - Try to move the window
   - Try to resize the window
   - Observe the progress bar

**What to verify:**
- [ ] Window can be moved during package loading
- [ ] Window can be resized during loading
- [ ] Title bar remains responsive
- [ ] Progress bar updates smoothly (not jerky)
- [ ] No "white out" or "Not Responding" in title bar
- [ ] Controls are disabled during operation
- [ ] Controls re-enable when done

**✅ PASS** if window stays responsive throughout
**❌ FAIL** if window freezes or becomes unresponsive

---

### Test 9: Disabled Features (30 seconds)

**Steps:**
1. Click **Search** button (grayed out)
2. Click **Install** button (grayed out)
3. Click **Uninstall** button (grayed out)

**What to verify:**
- [ ] Clicking Search shows info notification: "Coming Soon - Search functionality will be implemented in Phase 4"
- [ ] Clicking Install shows info notification: "Coming Soon - Install functionality will be implemented in Phase 3"
- [ ] Clicking Uninstall shows info notification: "Coming Soon - Uninstall functionality will be implemented in Phase 3"
- [ ] Notifications appear at top of window
- [ ] Notifications auto-dismiss after 3 seconds

**✅ PASS** if all show proper "Coming Soon" messages
**❌ FAIL** if buttons don't respond or show wrong message

---

### Test 10: Manager Switch Without Refresh (10 seconds)

**Steps:**
1. With packages loaded, change dropdown to different manager
2. Don't click Refresh yet

**What to verify:**
- [ ] Table clears immediately
- [ ] Status shows "Selected: [new manager]"
- [ ] No error occurs

**✅ PASS** if table clears cleanly
**❌ FAIL** if error or old data remains

---

### Test 11: Rapid Operations Test (1 minute)

**Steps:**
1. Click Refresh
2. **Immediately** try to click Refresh again
3. Wait for first operation to complete
4. Switch managers rapidly 3-4 times
5. Click Refresh

**What to verify:**
- [ ] Clicking Refresh while operation in progress shows warning: "Operation In Progress - Please wait..."
- [ ] No crashes from rapid clicking
- [ ] Switching managers doesn't cause errors
- [ ] Final refresh completes successfully

**✅ PASS** if no crashes or errors
**❌ FAIL** if app crashes or shows errors

---

### Test 12: Window Close and Reopen (30 seconds)

**Steps:**
1. Close the window (X button)
2. Relaunch: `python gui_pyqt6.py`
3. Select a manager and refresh

**What to verify:**
- [ ] Window closes cleanly (no errors in PowerShell)
- [ ] Relaunch works without issues
- [ ] All functionality still works

**✅ PASS** if clean close and restart
**❌ FAIL** if errors on close or restart

---

## Test Results Summary

Fill this out as you test:

| Test # | Test Name | Result | Notes |
|--------|-----------|--------|-------|
| 1 | Window Display | ☐ PASS ☐ FAIL | |
| 2 | WinGet Listing | ☐ PASS ☐ FAIL | |
| 3 | Chocolatey Listing | ☐ PASS ☐ FAIL | |
| 4 | Pip Listing | ☐ PASS ☐ FAIL | |
| 5 | NPM Listing | ☐ PASS ☐ FAIL | |
| 6 | Column Sorting | ☐ PASS ☐ FAIL | |
| 7 | Package Details | ☐ PASS ☐ FAIL | |
| 8 | UI Responsiveness | ☐ PASS ☐ FAIL | |
| 9 | Disabled Features | ☐ PASS ☐ FAIL | |
| 10 | Manager Switch | ☐ PASS ☐ FAIL | |
| 11 | Rapid Operations | ☐ PASS ☐ FAIL | |
| 12 | Window Close/Reopen | ☐ PASS ☐ FAIL | |

**Total Passed:** ____ / 12
**Total Failed:** ____ / 12

---

## What to Do If Tests Fail

**If you encounter errors:**
1. Note the exact error message
2. Note which test failed
3. Copy the PowerShell error output
4. Report back with details

**Common issues and fixes:**
- **"Package manager not found"** → That manager isn't installed, skip that test
- **"Permission denied"** → Some packages may require admin rights, this is expected
- **Slow loading** → Large package lists (100+) can take 10-15 seconds, this is normal

---

## Success Criteria

**Phase 2 is ready for v0.0.2b beta release if:**
- ✅ At least 10/12 tests pass
- ✅ All 4 package manager color coding tests pass (Tests 2-5)
- ✅ UI responsiveness test passes (Test 8)
- ✅ No crashes or critical errors

**Report your results when complete!**
