import base64, ctypes, hashlib, json, re, secrets, sqlite3, string, sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
DB = Path(__file__).resolve().with_name('PasswordSafe_Multi.db')
BG, WHITE, INK, MUTED, BLUE, NAV = '#edf2f8', '#ffffff', '#14243b', '#52647b', '#245bd8', '#14243b'
FONT = 'Segoe UI' if sys.platform == 'win32' else 'DejaVu Sans'
def strength(p):
    n = len(p); low = p.casefold()
    types = sum((any(c.islower() for c in p), any(c.isupper() for c in p), any(c.isdigit() for c in p), any(not c.isalnum() for c in p)))
    s = min(n * 3, 60) + types * 10
    s = min(s, 20 if n < 8 else 45 if n < 12 else 78 if n < 16 else 100)
    if any(x in low for x in ('password','qwerty','123456','admin','matkhau','abc123')): s = min(s, 15)
    elif re.search(r'(.)\1{2,}', p): s = min(s, 20)
    elif any(x in low for x in ('1234','abcd','asdf','zxcv')): s -= 15
    s = max(0, min(100, s))
    return (s, 'Chưa nhập' if not p else 'Yếu' if s < 40 else 'Trung bình' if s < 65 else 'Khá' if s < 85 else 'Mạnh')
def generate(n, symbols):
    groups = [string.ascii_lowercase, string.ascii_uppercase, string.digits] + (['!@#$%^&*_-+=?'] if symbols else [])
    chars = [secrets.choice(g) for g in groups]; pool = ''.join(groups)
    chars += [secrets.choice(pool) for _ in range(max(12, min(64, n)) - len(chars))]
    for i in range(len(chars)-1, 0, -1):
        j = secrets.randbelow(i+1); chars[i], chars[j] = chars[j], chars[i]
    return ''.join(chars)
class Store:
    def __init__(self, path=DB):
        self.db = sqlite3.connect(path); self.user = self.key = None
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, salt BLOB NOT NULL, verifier BLOB NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS vault (id INTEGER PRIMARY KEY, owner INTEGER NOT NULL REFERENCES users(id), secret BLOB NOT NULL)'); self.db.commit()
    def auth(self, name, password, register=False):
        self.user = self.key = None; name = name.strip().casefold()
        if not name or not password: raise ValueError('Nhập tên người dùng và mật khẩu.')
        row = self.db.execute('SELECT id,salt,verifier FROM users WHERE name=?', (name,)).fetchone()
        if register and (row or len(password) < 12): raise ValueError('Tên đã tồn tại hoặc mật khẩu dưới 12 ký tự.')
        if not register and not row: raise ValueError('Sai tên người dùng hoặc mật khẩu.')
        salt = secrets.token_bytes(16) if register else row[1]
        cipher = Fernet(base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)))
        if register:
            with self.db: uid = self.db.execute('INSERT INTO users(name,salt,verifier) VALUES (?,?,?)', (name,salt,cipher.encrypt(b'VAULT_OK'))).lastrowid
        else:
            if cipher.decrypt(row[2]) != b'VAULT_OK': raise ValueError('Không thể mở kho.')
            uid = row[0]
        self.user, self.key = uid, cipher
    def all(self):
        return [dict(json.loads(self.key.decrypt(blob)), id=ident) for ident,blob in self.db.execute('SELECT id,secret FROM vault WHERE owner=? ORDER BY id DESC',(self.user,))]
    def save(self, data, ident):
        blob = self.key.encrypt(json.dumps(data, ensure_ascii=False).encode())
        with self.db:
            if ident is None: self.db.execute('INSERT INTO vault(owner,secret) VALUES (?,?)',(self.user,blob))
            else: self.db.execute('UPDATE vault SET secret=? WHERE id=? AND owner=?',(blob,ident,self.user))
    def delete(self, ident):
        with self.db: self.db.execute('DELETE FROM vault WHERE id=? AND owner=?',(ident,self.user))
class App:
    def __init__(self, root):
        self.root = root; self.store = Store(); self.clip = None; self.records = []; self.edit = None
        root.title('Password Safe'); root.geometry('1100x700'); root.minsize(900,680); root.configure(bg=BG); root.protocol('WM_DELETE_WINDOW',self.close)
        style = ttk.Style(root); style.theme_use('clam'); root.option_add('*Font',(FONT,10))
        style.configure('TEntry',padding=6,fieldbackground=WHITE,foreground=INK,bordercolor='#ccd7e5',lightcolor=WHITE,darkcolor=WHITE)
        style.configure('TCheckbutton',background=WHITE,foreground=INK); style.map('TCheckbutton',background=[('active',WHITE)])
        style.configure('Treeview',background=WHITE,fieldbackground=WHITE,foreground=INK,rowheight=37,borderwidth=0,font=(FONT,10))
        style.configure('Treeview.Heading',background='#e8effa',foreground=INK,font=(FONT,10,'bold'),padding=9,relief='flat')
        style.map('Treeview',background=[('selected','#dce8ff')],foreground=[('selected',INK)])
        style.configure('TNotebook',background=BG,borderwidth=0); style.configure('TNotebook.Tab',padding=(20,10),font=(FONT,10,'bold'),background='#e0e8f4',foreground=MUTED); style.map('TNotebook.Tab',background=[('selected',WHITE)],foreground=[('selected',BLUE)])
        self.login_page()
    def clear(self):
        for w in self.root.winfo_children(): w.destroy()
    def label(self,parent,text,size=10,bold=False,color=INK):
        return tk.Label(parent,text=text,font=(FONT,size,'bold' if bold else 'normal'),fg=color,bg=parent.cget('bg'),anchor='w')
    def button(self,parent,text,fn,primary=False,danger=False):
        bg,fg = (BLUE,WHITE) if primary else ('#fdebec','#b42336') if danger else ('#e8effa',BLUE)
        b = tk.Button(parent,text=text,command=fn,bg=bg,fg=fg,activebackground='#1744b0' if primary else '#d5e2f5',activeforeground=WHITE if primary else fg,relief='flat',bd=0,padx=15,pady=9,cursor='hand2',font=(FONT,10,'bold'))
        b.bind('<Enter>',lambda e:b.configure(bg=b.cget('activebackground'),fg=b.cget('activeforeground'))); b.bind('<Leave>',lambda e:b.configure(bg=bg,fg=fg)); return b
    def field(self,parent,text,var,secret=False):
        self.label(parent,text,10,True,MUTED).pack(anchor='w',pady=(7,3))
        e = ttk.Entry(parent,textvariable=var,show='•' if secret else ''); e.pack(fill='x'); return e
    def login_page(self, register=False):
        self.clear(); self.register = register
        side = tk.Frame(self.root,bg=NAV,width=330); side.pack(side='left',fill='y'); side.pack_propagate(False)
        brand = tk.Frame(side,bg=NAV); brand.pack(anchor='w',padx=35,pady=55)
        self.label(brand,'PS',32,True,'#8eb5ff').pack(anchor='w'); self.label(brand,'Password\nSafe',28,True,WHITE).pack(anchor='w',pady=15); self.label(brand,'Kho mật khẩu cá nhân',12,False,'#b9c9df').pack(anchor='w')
        area = tk.Frame(self.root,bg=BG); area.pack(fill='both',expand=True)
        card = tk.Frame(area,bg=WHITE,padx=36,pady=30); card.place(relx=.5,rely=.5,anchor='center',width=440)
        self.label(card,'Đăng ký' if register else 'Đăng nhập',24,True).pack(anchor='w',pady=(0,8))
        self.name,self.master,self.confirm = (tk.StringVar() for _ in range(3))
        self.field(card,'Tên người dùng',self.name).focus_set(); pw = self.field(card,'Mật khẩu chính',self.master,True)
        if register: pw = self.field(card,'Nhập lại mật khẩu',self.confirm,True); self.label(card,'Tối thiểu 12 ký tự',9,False,MUTED).pack(anchor='w',pady=5)
        pw.bind('<Return>',lambda e:self.login()); self.button(card,'Tạo tài khoản' if register else 'Mở kho',self.login,True).pack(fill='x',pady=(22,10))
        self.button(card,'Đã có tài khoản? Đăng nhập' if register else 'Tạo tài khoản mới',lambda:self.login_page(not register)).pack(fill='x')
    def login(self):
        try:
            if self.register and self.master.get()!=self.confirm.get(): raise ValueError('Mật khẩu không khớp.')
            self.store.auth(self.name.get(),self.master.get(),self.register)
            self.records = self.store.all()
        except (ValueError,InvalidToken,sqlite3.Error) as e:
            self.store.user = self.store.key = None
            messagebox.showerror('Lỗi',str(e) or 'Sai mật khẩu hoặc dữ liệu lỗi.'); return
        self.username = self.name.get().strip().casefold()
        self.master.set(''); self.confirm.set(''); self.main_page()
    def main_page(self):
        self.clear(); bar = tk.Frame(self.root,bg=NAV,padx=25,pady=15); bar.pack(fill='x')
        self.label(bar,'PS  /  Password Safe',19,True,WHITE).pack(side='left'); self.button(bar,'Đăng xuất',self.lock).pack(side='right'); self.label(bar,self.username,11,True,'#c6d5ee').pack(side='right',padx=18)
        body = tk.Frame(self.root,bg=BG,padx=24,pady=20); body.pack(fill='both',expand=True)
        head = tk.Frame(body,bg=BG); head.pack(fill='x',pady=(0,15)); self.label(head,'Kho cá nhân',23,True).pack(side='left'); self.count = self.label(head,'',11,True,BLUE); self.count.pack(side='right')
        self.tabs = ttk.Notebook(body); self.tabs.pack(fill='both',expand=True)
        self.vault = tk.Frame(self.tabs,bg=BG,padx=0,pady=12); self.tools = tk.Frame(self.tabs,bg=BG,pady=12)
        self.tabs.add(self.vault,text='Kho mật khẩu'); self.tabs.add(self.tools,text='Tạo & kiểm tra'); self.vault_page(); self.tools_page()
    def vault_page(self):
        left = tk.Frame(self.vault,bg=WHITE,padx=18,pady=16); left.pack(side='left',fill='both',expand=True,padx=(0,12))
        self.label(left,'Danh sách tài khoản',15,True).pack(anchor='w'); self.query = tk.StringVar(); self.field(left,'Tìm kiếm',self.query)
        wrap = tk.Frame(left,bg=WHITE); wrap.pack(fill='both',expand=True,pady=(14,0)); self.table = ttk.Treeview(wrap,columns=('service','username','score'),show='headings',selectmode='browse')
        for key,text,width in [('service','Dịch vụ',140),('username','Tên đăng nhập',170),('score','Độ mạnh',105)]:
            self.table.heading(key,text=text); self.table.column(key,width=width,minwidth=65,stretch=key!='score')
        scroll = ttk.Scrollbar(wrap,command=self.table.yview); scroll.pack(side='right',fill='y'); self.table.configure(yscrollcommand=scroll.set); self.table.pack(fill='both',expand=True)
        right = tk.Frame(self.vault,bg=WHITE,padx=18,pady=16,width=325); right.pack(side='right',fill='y'); right.pack_propagate(False)
        self.form_title = self.label(right,'Thêm tài khoản',15,True); self.form_title.pack(anchor='w'); self.fields = {}
        for key,text in [('service','Dịch vụ'),('username','Tên đăng nhập'),('password','Mật khẩu'),('website','Website')]:
            self.fields[key] = tk.StringVar(); entry = self.field(right,text,self.fields[key],key=='password')
            if key=='password': self.pw_entry = entry
        self.reveal = tk.BooleanVar(value=False)
        ttk.Checkbutton(right,text='Hiện mật khẩu',variable=self.reveal,command=lambda:self.pw_entry.configure(show='' if self.reveal.get() else '•')).pack(anchor='w',pady=5)
        actions = tk.Frame(right,bg=WHITE); actions.pack(fill='x'); actions.columnconfigure((0,1),weight=1)
        for i,(text,fn) in enumerate([('Lưu',self.save),('Thêm mới',self.reset),('Sao chép',lambda:self.copy(self.fields['password'].get())),('Xóa',self.delete)]):
            self.button(actions,text,fn,i==0,i==3).grid(row=i//2,column=i%2,sticky='ew',padx=3,pady=3)
        self.query.trace_add('write',lambda *_:self.search_changed()); self.table.bind('<<TreeviewSelect>>',self.select); self.reset(); self.refresh()
    def search_changed(self):
        self.reset(); self.refresh()
    def refresh(self):
        self.table.delete(*self.table.get_children()); term = self.query.get().strip().casefold(); self.count.configure(text=f'{len(self.records)} tài khoản')
        for r in self.records:
            if term in ' '.join(r.get(k,'') for k in ('service','username','website')).casefold(): self.table.insert('','end',iid=str(r['id']),values=(r['service'],r['username'],strength(r['password'])[1]))
    def select(self,event=None):
        if not self.table.selection(): return
        r = next(r for r in self.records if r['id']==int(self.table.selection()[0])); self.edit = r['id']
        self.form_title.configure(text='Sửa tài khoản')
        self.reveal.set(False); self.pw_entry.configure(show='•')
        for k,v in self.fields.items(): v.set(r.get(k,''))
    def reset(self):
        self.edit = None; self.form_title.configure(text='Thêm tài khoản')
        self.table.selection_remove(self.table.selection())
        self.reveal.set(False); self.pw_entry.configure(show='•')
        for v in self.fields.values(): v.set('')
    def save(self):
        data = {k:v.get() if k=='password' else v.get().strip() for k,v in self.fields.items()}
        if not all(data[k] for k in ('service','username','password')): messagebox.showwarning('Thiếu dữ liệu','Nhập dịch vụ, tên đăng nhập và mật khẩu.'); return
        try: self.store.save(data,self.edit); self.records = self.store.all(); self.reset(); self.refresh()
        except (sqlite3.Error,InvalidToken): messagebox.showerror('Lỗi','Không thể lưu dữ liệu.')
    def delete(self):
        if self.edit is not None and messagebox.askyesno('Xóa','Xóa tài khoản này?'):
            try: self.store.delete(self.edit); self.records = self.store.all(); self.reset(); self.refresh()
            except sqlite3.Error: messagebox.showerror('Lỗi','Không thể xóa dữ liệu.')
    def tools_page(self):
        card = tk.Frame(self.tools,bg=WHITE,padx=30,pady=22); card.pack(fill='both',expand=True)
        self.label(card,'Tạo & kiểm tra mật khẩu',19,True).pack(anchor='w'); self.test = tk.StringVar(); entry = self.field(card,'Mật khẩu',self.test,True)
        self.show_test = tk.BooleanVar(value=False); ttk.Checkbutton(card,text='Hiện mật khẩu',variable=self.show_test,command=lambda:entry.configure(show='' if self.show_test.get() else '•')).pack(anchor='w',pady=8)
        self.rating = self.label(card,'',21,True); self.rating.pack(anchor='w',pady=(5,7)); self.meter = tk.Canvas(card,height=12,bg='#e0e8f4',highlightthickness=0); self.meter.pack(fill='x')
        self.tip = self.label(card,'',10,False,MUTED); self.tip.pack(anchor='w',pady=8)
        tk.Frame(card,bg='#e0e8f4',height=1).pack(fill='x',pady=10); self.label(card,'Tạo mật khẩu',15,True).pack(anchor='w')
        options = tk.Frame(card,bg=WHITE); options.pack(fill='x',pady=10); self.label(options,'Độ dài (12–64)',10,True).pack(side='left'); self.length = tk.IntVar(value=20); self.symbols = tk.BooleanVar(value=True)
        ttk.Spinbox(options,from_=12,to=64,textvariable=self.length,width=5).pack(side='left',padx=12); ttk.Checkbutton(options,text='Ký tự đặc biệt',variable=self.symbols).pack(side='left')
        buttons = tk.Frame(card,bg=WHITE); buttons.pack(anchor='w',pady=8)
        for i,(text,fn) in enumerate([('Tạo mật khẩu',self.regenerate),('Sao chép',lambda:self.copy(self.test.get())),('Dùng để lưu',self.use_password)]): self.button(buttons,text,fn,i==0).pack(side='left',padx=(0,8))
        self.test.trace_add('write',lambda *_:self.update_strength()); self.meter.bind('<Configure>',lambda e:self.update_strength()); self.update_strength()
    def update_strength(self):
        s,level = strength(self.test.get()); color = '#d63a4e' if s<40 else '#c47b10' if s<65 else BLUE if s<85 else '#16865f'
        self.rating.configure(text=f'{s}/100  ·  {level}',fg=color); self.meter.delete('all'); self.meter.create_rectangle(0,0,self.meter.winfo_width()*s/100,12,fill=color,width=0)
        p = self.test.get()
        if not p: tip = 'Nhập hoặc tạo mật khẩu.'
        elif len(p)<12: tip = 'Nên dùng ít nhất 12 ký tự.'
        elif s<40: tip = 'Tránh chuỗi phổ biến và ký tự lặp.'
        elif s<85: tip = 'Tăng độ dài và tính ngẫu nhiên.'
        else: tip = 'Dùng mật khẩu riêng cho từng dịch vụ.'
        self.tip.configure(text=tip)
    def regenerate(self):
        try: n = self.length.get()
        except tk.TclError: n = 20
        n = max(12,min(64,n)); self.length.set(n); self.test.set(generate(n,self.symbols.get()))
    def use_password(self):
        if self.test.get(): self.reset(); self.fields['password'].set(self.test.get()); self.tabs.select(self.vault)
    def copy(self,value):
        if value: self.root.clipboard_clear(); self.root.clipboard_append(value); self.clip = value; self.root.after(20000,lambda:self.clear_copy(value))
    def clear_copy(self,value):
        try:
            if self.root.clipboard_get()==value: self.root.clipboard_clear()
        except tk.TclError: pass
        if self.clip==value: self.clip = None
    def lock(self):
        if self.clip: self.clear_copy(self.clip)
        for v in self.fields.values(): v.set('')
        self.test.set(''); self.store.user = self.store.key = None
        self.records = []; self.edit = None; self.login_page()
    def close(self):
        if self.clip: self.clear_copy(self.clip)
        self.store.user = self.store.key = None; self.store.db.close(); self.root.destroy()
if __name__=='__main__':
    if sys.platform=='win32':
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (OSError,AttributeError): pass
    App(tk.Tk()).root.mainloop()
