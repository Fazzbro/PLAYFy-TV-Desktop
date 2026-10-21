from elftools.elf.elffile import ELFFile
import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    for sec in elf.iter_sections():
        if sec['sh_addr'] <= 0x6b4c0 < sec['sh_addr'] + sec['sh_size']:
            sec_addr = sec['sh_addr']
            sec_data = sec.data()
            off = 0x6b4c0 - sec_addr
            chunk = sec_data[off:off+3361]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            print("=== Tracing r12 (lora) in ohMyYes ===")
            for ins in md.disasm(chunk, 0x6b4c0):
                if 'r12' in ins.op_str and ins.address < 0x6b800:
                    print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
