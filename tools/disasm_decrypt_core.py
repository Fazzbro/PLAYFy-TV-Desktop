from elftools.elf.elffile import ELFFile
import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    for sec in elf.iter_sections():
        if sec['sh_addr'] <= 0x6bb80 < sec['sh_addr'] + sec['sh_size']:
            sec_addr = sec['sh_addr']
            sec_data = sec.data()
            off = 0x6bb80 - sec_addr
            chunk = sec_data[off:off+300]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            print("=== Disassembly at 0x6bb80 ===")
            for ins in md.disasm(chunk, 0x6bb80):
                print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
