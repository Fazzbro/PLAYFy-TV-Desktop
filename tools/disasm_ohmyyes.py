import capstone
from elftools.elf.elffile import ELFFile

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    symtab = elf.get_section_by_name('.dynsym')
    sym = [s for s in symtab.iter_symbols() if s.name == 'Java_com_playfy_tv_helpers_NintyMin_ohMyYes'][0]
    val = sym['st_value']
    size = sym['st_size']
    print(f"Java_com_playfy_tv_helpers_NintyMin_ohMyYes: 0x{val:x}, size {size}")

    for sec in elf.iter_sections():
        if sec['sh_addr'] <= val < sec['sh_addr'] + sec['sh_size']:
            off = val - sec['sh_addr']
            chunk = sec.data()[off:off+256]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            for ins in md.disasm(chunk, val):
                print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
