#!/usr/bin/env bash
# Download reference documents and drivers for the machine into drv/<device or computer>/.
# drv/ is git-ignored. Re-run to fill in anything missing. Run from WSL in the bios folder.
set -u
cd "$(dirname "$0")/.."
UA="Mozilla/5.0 (X11; Linux x86_64) bios-teardown-fetch"
get() {  # get <dir> <url> [filename]
  local dir="$1" url="$2" name="${3:-$(basename "${2%%\?*}")}"
  mkdir -p "drv/$dir"
  if [ -s "drv/$dir/$name" ]; then echo "have   drv/$dir/$name"; return; fi
  if curl -fsSL --max-time 300 -A "$UA" -o "drv/$dir/$name.part" "$url"; then
    mv "drv/$dir/$name.part" "drv/$dir/$name"; printf 'got    drv/%s/%s (%s bytes)\n' "$dir" "$name" "$(stat -c %s "drv/$dir/$name")"
  else
    rm -f "drv/$dir/$name.part"; echo "FAILED $url"
  fi
}

# --- video: Chips & Technologies 65535 ---------------------------------------------------
get video-ct65535 "https://cs.nyu.edu/~mwalfish/classes/ut/f09-cs395t/ref/hardware/vgadoc/CHIPS.TXT"
get video-ct65535 "https://pdos.csail.mit.edu/6.828/2008/readings/hardware/vgadoc/VGABIOS.TXT"
get video-ct65535 "https://pdos.csail.mit.edu/6.828/2016/readings/hardware/vgadoc/VGAREGS.TXT"
# --- chipset: PicoPower (Evergreen PT86C268 datasheet not online; related family docs) ---------
get chipset-picopower "http://www.bitsavers.org/components/picoPower/PT86C768_Redwood1_2_199404.pdf"
get chipset-picopower "http://www.bitsavers.org/components/picoPower/AN928_Active_Power_Management_Using_SuperIO_1994.pdf"
get chipset-picopower "http://www.bitsavers.org/components/picoPower/PT82C206F-LV_Integrated_Peripheral_Controller.pdf"
get chipset-picopower "https://files.mpoli.fi/unpacked/software/dos/utils/misc/tlb_v252.zip/chipset.doc" picopower-chipset-list-tlb.doc
# --- power management: PhoenixMISER / PHDISK ---------------------------------------------------
get power-phoenixmiser "https://archive.org/download/cd-rom_and_phdisk/cd-rom_and_phdisk_archive.torrent"
get power-phoenixmiser "https://archive.org/download/cd-rom_and_phdisk/" phdisk-archive-listing.html
# --- network: UMC UM9003AF (dock NE2000) -------------------------------------------------------
get network-um9003af "https://files.elektroda.pl/3934,um9003af.html" elektroda-um9003af-page.html
# --- computer: CompuAdd utilities disks --------------------------------------------------------
get computer-compuadd "https://archive.org/download/compuadd286386486utilitiesanddrivers/" compuadd-utilities-listing.html
get computer-compuadd "https://archive.org/download/compuadd286386486utilitiesanddrivers/CompuAdd_386_486_Mouse_360k.img"
get computer-compuadd "https://archive.org/download/compuadd286386486utilitiesanddrivers/CompuAdd_386_486_System_Utilities_1.2MB.img"
get computer-compuadd "https://archive.org/download/compuadd286386486utilitiesanddrivers/CompuAdd_386_486_VGA_Disk1_1.2MB.img"
get computer-compuadd "https://archive.org/download/compuadd286386486utilitiesanddrivers/CompuAdd_386_486_VGA_Disk2_1.2MB.img"
# --- computer: Chaplet references ------------------------------------------------------------
get computer-chaplet "https://www.macdat.net/laptops/chaplet/ilufa_750.php" macdat-ilufa-750.html
get computer-chaplet "https://www.macdat.net/laptops/chaplet/halikan_nbd486.php" macdat-halikan-nbd486.html
get computer-chaplet "https://www.macdat.net/laptops/chaplet_home.html" macdat-chaplet-home.html
get computer-chaplet "https://fccid.io/GXL" fccid-chaplet-GXL.html
# --- pointing device: CuteMouse PS/2 driver -----------------------------------------------------
get mouse-ps2 "https://www.ibiblio.org/pub/micro/pc-stuff/freedos/files/dos/ctmouse/2.1b4/ctmouse.zip" ctmouse-2.1b4.zip
get mouse-ps2 "http://cutemouse.sourceforge.net/" cutemouse-home.html
# --- alternates found later -------------------------------------------------------------------
get power-phoenixmiser "https://archive.org/download/cd-rom_and_phdisk/Disk1.img" phdisk17-disk1.img
# vogonsdrivers needs a browser session; try with a referer, keep only if it is a zip
for id in 838 854; do
  f="drv/network-um9003af/vogons-$id.zip"; mkdir -p drv/network-um9003af
  [ -s "$f" ] && continue
  curl -fsSL --max-time 300 -A "$UA" -e "https://vogonsdrivers.com/index.php?catid=17" -o "$f" "https://vogonsdrivers.com/getfile.php?fileid=$id&menustate=0" \
    && { file "$f" | grep -q "Zip archive" && echo "got    $f" || { echo "not a zip: vogons $id"; rm -f "$f"; }; }
done

# --- XTIDE Universal BIOS r638 release binaries (only used to compare against the source build) ---
for f in ide_386.bin ide_386l.bin ide_at.bin ide_xt.bin ide_tiny.bin xtidecfg.com biosdrvs.com; do get xtide "https://www.xtideuniversalbios.org/binaries/r638/$f"; done
