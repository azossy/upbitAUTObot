/// 앱 다국어 문자열. 약 15개국 언어 지원.
/// [locale] 예: 'ko', 'en', 'zh', 'ja' ...
class AppLocalizations {
  AppLocalizations(this.locale);
  final String locale;

  static const List<String> supportedLocales = [
    'ko', 'en', 'zh', 'ja', 'es', 'fr', 'de', 'pt', 'ru', 'ar', 'th', 'vi', 'id', 'hi', 'tr',
  ];

  static const Map<String, String> languageNames = {
    'ko': '한국어',
    'en': 'English',
    'zh': '中文',
    'ja': '日本語',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'pt': 'Português',
    'ru': 'Русский',
    'ar': 'العربية',
    'th': 'ไทย',
    'vi': 'Tiếng Việt',
    'id': 'Bahasa Indonesia',
    'hi': 'हिन्दी',
    'tr': 'Türkçe',
  };

  String _t(Map<String, Map<String, String>> all, String key) {
    return all[key]?[locale] ?? all[key]?['en'] ?? key;
  }

  static final Map<String, Map<String, String>> _strings = {
    'appTitle': {
      'ko': '배짱이',
      'en': 'Upbit Auto Trading',
      'zh': 'Upbit 自动交易',
      'ja': 'Upbit 自動売買',
      'es': 'Upbit Trading Automático',
      'fr': 'Upbit Trading Auto',
      'de': 'Upbit Auto-Handel',
      'pt': 'Upbit Trading Automático',
      'ru': 'Upbit Автотрейдинг',
      'ar': 'Upbit تداول تلقائي',
      'th': 'Upbit เทรดอัตโนมัติ',
      'vi': 'Upbit Giao dịch Tự động',
      'id': 'Upbit Trading Otomatis',
      'hi': 'Upbit ऑटो ट्रेडिंग',
      'tr': 'Upbit Otomatik İşlem',
    },
    'navDashboard': {'ko': '대시보드', 'en': 'Dashboard', 'zh': '仪表板', 'ja': 'ダッシュボード', 'es': 'Panel', 'fr': 'Tableau de bord', 'de': 'Dashboard', 'pt': 'Painel', 'ru': 'Панель', 'ar': 'لوحة التحكم', 'th': 'แดชบอร์ด', 'vi': 'Bảng điều khiển', 'id': 'Dasbor', 'hi': 'डैशबोर्ड', 'tr': 'Kontrol Paneli'},
    'navPositions': {'ko': '포지션', 'en': 'Positions', 'zh': '持仓', 'ja': 'ポジション', 'es': 'Posiciones', 'fr': 'Positions', 'de': 'Positionen', 'pt': 'Posições', 'ru': 'Позиции', 'ar': 'المراكز', 'th': 'ตำแหน่ง', 'vi': 'Vị thế', 'id': 'Posisi', 'hi': 'पोजिशन', 'tr': 'Pozisyonlar'},
    'navTrades': {'ko': '거래내역', 'en': 'Trades', 'zh': '交易记录', 'ja': '取引履歴', 'es': 'Operaciones', 'fr': 'Transactions', 'de': 'Trades', 'pt': 'Negociações', 'ru': 'Сделки', 'ar': 'الصفقات', 'th': 'การซื้อขาย', 'vi': 'Giao dịch', 'id': 'Transaksi', 'hi': 'ट्रेड', 'tr': 'İşlemler'},
    'navNews': {'ko': '뉴스', 'en': 'News', 'zh': '新闻', 'ja': 'ニュース', 'es': 'Noticias', 'fr': 'Actualités', 'de': 'Nachrichten', 'pt': 'Notícias', 'ru': 'Новости', 'ar': 'أخبار', 'th': 'ข่าว', 'vi': 'Tin tức', 'id': 'Berita', 'hi': 'समाचार', 'tr': 'Haberler'},
    'navMy': {'ko': 'My', 'en': 'My', 'zh': '我的', 'ja': 'マイ', 'es': 'Mi', 'fr': 'Mon', 'de': 'Mein', 'pt': 'Meu', 'ru': 'Моё', 'ar': 'خاصتي', 'th': 'ของฉัน', 'vi': 'Của tôi', 'id': 'Saya', 'hi': 'मेरा', 'tr': 'Benim'},
    'myTitle': {'ko': 'My', 'en': 'My', 'zh': '我的', 'ja': 'マイ', 'es': 'Mi cuenta', 'fr': 'Mon compte', 'de': 'Mein Konto', 'pt': 'Minha conta', 'ru': 'Моё', 'ar': 'خاصتي', 'th': 'ของฉัน', 'vi': 'Của tôi', 'id': 'Akun Saya', 'hi': 'मेरा', 'tr': 'Hesabım'},
    'profile': {'ko': '프로필', 'en': 'Profile', 'zh': '个人资料', 'ja': 'プロフィール', 'es': 'Perfil', 'fr': 'Profil', 'de': 'Profil', 'pt': 'Perfil', 'ru': 'Профиль', 'ar': 'الملف الشخصي', 'th': 'โปรไฟล์', 'vi': 'Hồ sơ', 'id': 'Profil', 'hi': 'प्रोफ़ाइल', 'tr': 'Profil'},
    'nickname': {'ko': '별명', 'en': 'Nickname', 'zh': '昵称', 'ja': 'ニックネーム', 'es': 'Apodo', 'fr': 'Pseudo', 'de': 'Spitzname', 'pt': 'Apelido', 'ru': 'Ник', 'ar': 'اللقب', 'th': 'ชื่อเล่น', 'vi': 'Biệt danh', 'id': 'Nickname', 'hi': 'उपनाम', 'tr': 'Takma ad'},
    'email': {'ko': '이메일', 'en': 'Email', 'zh': '邮箱', 'ja': 'メール', 'es': 'Correo', 'fr': 'E-mail', 'de': 'E-Mail', 'pt': 'E-mail', 'ru': 'Email', 'ar': 'البريد', 'th': 'อีเมล', 'vi': 'Email', 'id': 'Email', 'hi': 'ईमेल', 'tr': 'E-posta'},
    'profilePhoto': {'ko': '프로필 사진', 'en': 'Profile photo', 'zh': '头像', 'ja': 'プロフィール写真', 'es': 'Foto de perfil', 'fr': 'Photo de profil', 'de': 'Profilfoto', 'pt': 'Foto do perfil', 'ru': 'Фото', 'ar': 'الصورة', 'th': 'รูปโปรไฟล์', 'vi': 'Ảnh đại diện', 'id': 'Foto profil', 'hi': 'प्रोफ़ाइल फोटो', 'tr': 'Profil fotoğrafı'},
    'photoUrlHint': {'ko': '이미지 URL 입력', 'en': 'Enter image URL', 'zh': '输入图片链接', 'ja': '画像URLを入力', 'es': 'URL de imagen', 'fr': 'URL de l\'image', 'de': 'Bild-URL', 'pt': 'URL da imagem', 'ru': 'URL изображения', 'ar': 'رابط الصورة', 'th': 'URL รูปภาพ', 'vi': 'Nhập URL ảnh', 'id': 'URL gambar', 'hi': 'छवि URL', 'tr': 'Görsel URL'},
    'photoCamera': {'ko': '카메라로 촬영', 'en': 'Take photo', 'zh': '拍照', 'ja': 'カメラで撮影', 'es': 'Tomar foto', 'fr': 'Prendre une photo', 'de': 'Foto aufnehmen', 'pt': 'Tirar foto', 'ru': 'Сфотографировать', 'ar': 'التقاط صورة', 'th': 'ถ่ายรูป', 'vi': 'Chụp ảnh', 'id': 'Ambil foto', 'hi': 'फोटो लें', 'tr': 'Fotoğraf çek'},
    'photoAlbum': {'ko': '앨범에서 선택', 'en': 'Choose from album', 'zh': '从相册选择', 'ja': 'アルバムから選択', 'es': 'Elegir del álbum', 'fr': 'Choisir dans l\'album', 'de': 'Aus Album wählen', 'pt': 'Escolher do álbum', 'ru': 'Выбрать из альбома', 'ar': 'اختر من الألبوم', 'th': 'เลือกจากอัลบัม', 'vi': 'Chọn từ thư viện', 'id': 'Pilih dari album', 'hi': 'ऐल्बम से चुनें', 'tr': 'Albümden seç'},
    'save': {'ko': '저장', 'en': 'Save', 'zh': '保存', 'ja': '保存', 'es': 'Guardar', 'fr': 'Enregistrer', 'de': 'Speichern', 'pt': 'Salvar', 'ru': 'Сохранить', 'ar': 'حفظ', 'th': 'บันทึก', 'vi': 'Lưu', 'id': 'Simpan', 'hi': 'सहेजें', 'tr': 'Kaydet'},
    'language': {'ko': '언어', 'en': 'Language', 'zh': '语言', 'ja': '言語', 'es': 'Idioma', 'fr': 'Langue', 'de': 'Sprache', 'pt': 'Idioma', 'ru': 'Язык', 'ar': 'اللغة', 'th': 'ภาษา', 'vi': 'Ngôn ngữ', 'id': 'Bahasa', 'hi': 'भाषा', 'tr': 'Dil'},
    'languageSelect': {'ko': '앱 표시 언어를 선택하세요', 'en': 'Select app language', 'zh': '选择应用语言', 'ja': '表示言語を選択', 'es': 'Seleccionar idioma', 'fr': 'Choisir la langue', 'de': 'Sprache wählen', 'pt': 'Selecionar idioma', 'ru': 'Выберите язык', 'ar': 'اختر اللغة', 'th': 'เลือกภาษา', 'vi': 'Chọn ngôn ngữ', 'id': 'Pilih bahasa', 'hi': 'भाषा चुनें', 'tr': 'Dil seçin'},
    'botSettings': {'ko': '봇 설정', 'en': 'Bot settings', 'zh': '机器人设置', 'ja': 'ボット設定', 'es': 'Config. del bot', 'fr': 'Paramètres du bot', 'de': 'Bot-Einstellungen', 'pt': 'Config. do bot', 'ru': 'Настройки бота', 'ar': 'إعدادات البوت', 'th': 'การตั้งค่าบอท', 'vi': 'Cài đặt bot', 'id': 'Pengaturan bot', 'hi': 'बॉट सेटिंग', 'tr': 'Bot ayarları'},
    'passwordChange': {'ko': '비밀번호 변경', 'en': 'Change password', 'zh': '修改密码', 'ja': 'パスワード変更', 'es': 'Cambiar contraseña', 'fr': 'Changer le mot de passe', 'de': 'Passwort ändern', 'pt': 'Alterar senha', 'ru': 'Сменить пароль', 'ar': 'تغيير كلمة المرور', 'th': 'เปลี่ยนรหัสผ่าน', 'vi': 'Đổi mật khẩu', 'id': 'Ubah kata sandi', 'hi': 'पासवर्ड बदलें', 'tr': 'Şifre değiştir'},
    'logout': {'ko': '로그아웃', 'en': 'Log out', 'zh': '退出登录', 'ja': 'ログアウト', 'es': 'Cerrar sesión', 'fr': 'Déconnexion', 'de': 'Abmelden', 'pt': 'Sair', 'ru': 'Выйти', 'ar': 'تسجيل الخروج', 'th': 'ออกจากระบบ', 'vi': 'Đăng xuất', 'id': 'Keluar', 'hi': 'लॉग आउट', 'tr': 'Çıkış'},
    'login': {'ko': '로그인', 'en': 'Log in', 'zh': '登录', 'ja': 'ログイン', 'es': 'Iniciar sesión', 'fr': 'Connexion', 'de': 'Anmelden', 'pt': 'Entrar', 'ru': 'Вход', 'ar': 'تسجيل الدخول', 'th': 'เข้าสู่ระบบ', 'vi': 'Đăng nhập', 'id': 'Masuk', 'hi': 'लॉग इन', 'tr': 'Giriş'},
    'register': {'ko': '회원가입', 'en': 'Register', 'zh': '注册', 'ja': '新規登録', 'es': 'Registrarse', 'fr': 'S\'inscrire', 'de': 'Registrieren', 'pt': 'Cadastrar', 'ru': 'Регистрация', 'ar': 'التسجيل', 'th': 'สมัครสมาชิก', 'vi': 'Đăng ký', 'id': 'Daftar', 'hi': 'रजिस्टर', 'tr': 'Kayıt'},
    'settings': {'ko': '설정', 'en': 'Settings', 'zh': '设置', 'ja': '設定', 'es': 'Ajustes', 'fr': 'Paramètres', 'de': 'Einstellungen', 'pt': 'Configurações', 'ru': 'Настройки', 'ar': 'الإعدادات', 'th': 'การตั้งค่า', 'vi': 'Cài đặt', 'id': 'Pengaturan', 'hi': 'सेटिंग', 'tr': 'Ayarlar'},
    'saved': {'ko': '저장되었습니다', 'en': 'Saved', 'zh': '已保存', 'ja': '保存しました', 'es': 'Guardado', 'fr': 'Enregistré', 'de': 'Gespeichert', 'pt': 'Salvo', 'ru': 'Сохранено', 'ar': 'تم الحفظ', 'th': 'บันทึกแล้ว', 'vi': 'Đã lưu', 'id': 'Tersimpan', 'hi': 'सहेजा गया', 'tr': 'Kaydedildi'},
    'newsNoticeTitle': {'ko': '뉴스·공지', 'en': 'News & Notices', 'zh': '新闻与公告', 'ja': 'ニュース・お知らせ', 'es': 'Noticias y avisos', 'fr': 'Actualités et avis', 'de': 'Nachrichten & Hinweise', 'pt': 'Notícias e avisos', 'ru': 'Новости и уведомления', 'ar': 'الأخبار والإشعارات', 'th': 'ข่าวและประกาศ', 'vi': 'Tin tức & Thông báo', 'id': 'Berita & Pengumuman', 'hi': 'समाचार और सूचना', 'tr': 'Haberler ve Duyurular'},
  };

  String get appTitle => _t(_strings, 'appTitle');
  String get navDashboard => _t(_strings, 'navDashboard');
  String get navPositions => _t(_strings, 'navPositions');
  String get navTrades => _t(_strings, 'navTrades');
  String get navNews => _t(_strings, 'navNews');
  String get navMy => _t(_strings, 'navMy');
  String get myTitle => _t(_strings, 'myTitle');
  String get profile => _t(_strings, 'profile');
  String get nickname => _t(_strings, 'nickname');
  String get email => _t(_strings, 'email');
  String get profilePhoto => _t(_strings, 'profilePhoto');
  String get photoUrlHint => _t(_strings, 'photoUrlHint');
  String get photoCamera => _t(_strings, 'photoCamera');
  String get photoAlbum => _t(_strings, 'photoAlbum');
  String get save => _t(_strings, 'save');
  String get language => _t(_strings, 'language');
  String get languageSelect => _t(_strings, 'languageSelect');
  String get botSettings => _t(_strings, 'botSettings');
  String get passwordChange => _t(_strings, 'passwordChange');
  String get logout => _t(_strings, 'logout');
  String get login => _t(_strings, 'login');
  String get register => _t(_strings, 'register');
  String get settings => _t(_strings, 'settings');
  String get saved => _t(_strings, 'saved');
  String get newsNoticeTitle => _t(_strings, 'newsNoticeTitle');
}
