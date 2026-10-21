from elftools.elf.elffile import ELFFile
import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    text_sec = elf.get_section_by_name('.text')
    sec_addr = text_sec['sh_addr']
    sec_data = text_sec.data()
    off = 0x69b00 - sec_addr
    chunk = sec_data[off:off+300]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    print("=== Disassembly around 0x69b00 ===")
    for ins in md.disasm(chunk, 0x69b00):
        print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
