import os

path = r'c:\Users\91934\OneDrive\Desktop\Jaga\Ecommerce\templates\store\checkout.html'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Target broken pattern
    broken = 'const baseTotal = {{ cart_total.total_price }\n  };'
    fixed = 'const baseTotal = {{ cart_total.total_price }};'
    
    if broken in content:
        content = content.replace(broken, fixed)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed broken syntax.")
    elif fixed in content:
        print("File is already fixed.")
    else:
        print("Pattern not found. Content around expected area:")
        idx = content.find('const baseTotal')
        if idx != -1:
            print(content[idx:idx+100])
        else:
            print("baseTotal not found.")
else:
    print("File not found.")
