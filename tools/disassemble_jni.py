import os
from elftools.elf.elffile import ELFFile
import capstone

def disassemble_func(so_path, func_name):
    print(f"\n==================== Disassembling {func_name} in {so_path} ====================")
    with open(so_path, 'rb') as f:
        elf = ELFFile(f)
        symtab = elf.get_section_by_name('.dynsym') or elf.get_section_by_name('.symtab')
        if not symtab:
            print("No symbol table found")
            return
        
        target_sym = None
        for sym in symtab.iter_symbols():
            if sym.name == func_name:
                target_sym = sym
                break
        
        if not target_sym:
            print(f"Symbol {func_name} not found")
            return
        
        print(f"Symbol: {target_sym.name}, Value: 0x{target_sym['st_value']:x}, Size: {target_sym['st_size']}")
        
        # Find section containing the symbol
        for section in elf.iter_sections():
            sec_addr = section['sh_addr']
            sec_size = section['sh_size']
            if sec_addr <= target_sym['st_value'] < sec_addr + sec_size:
                offset_in_sec = target_sym['st_value'] - sec_addr
                f_size = target_sym['st_size'] if target_sym['st_size'] > 0 else 512
                f_data = section.data()[offset_in_sec:offset_in_sec + f_size]
                
                md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
                for ins in md.disasm(f_data, target_sym['st_value']):
                    print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
                break

disassemble_func(r'apk_extracted\lib\x86_64\libumairi-lib.so', 'Java_com_playfy_tv_helpers_NintyMin_ohMyNo')
disassemble_func(r'apk_extracted\lib\x86_64\libnative-lib.so', 'Java_com_playfy_tv_helpers_NintyMin_ohMyYes')
