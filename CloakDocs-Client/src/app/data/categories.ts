// Ana konu başlıkları ve alt başlıklar
export const MAIN_CATEGORIES = [
  {
    id: 1,
    name: "Yapay Zeka ve Makine Öğrenimi",
    icon: "🧠",
    subcategories: [
      { 
        id: 101, 
        name: "Derin Öğrenme",
        keywords: ["deep learning", "neural network", "CNN", "RNN", "LSTM", "transformer", "yapay sinir ağları", "derin öğrenme", "sinir ağları", "evrişimli sinir ağları", "derin sinir ağları", "öznitelik çıkarımı", "backpropagation", "attention mechanism", "dikkat mekanizması", "GAN", "üretici çekişmeli ağlar"]
      },
      { 
        id: 102, 
        name: "Doğal Dil İşleme",
        keywords: ["NLP", "doğal dil işleme", "NLU", "dil modeli", "language model", "BERT", "GPT", "sentiment analysis", "duygu analizi", "metin sınıflandırma", "text classification", "named entity recognition", "varlık ismi tanıma", "summarization", "özetleme", "machine translation", "makine çevirisi", "chatbot", "sohbet robotu", "transformers", "word2vec", "kelime gömme", "word embedding"]
      },
      { 
        id: 103, 
        name: "Bilgisayarla Görü",
        keywords: ["computer vision", "bilgisayarlı görü", "görüntü işleme", "image processing", "object detection", "nesne tespiti", "face recognition", "yüz tanıma", "image segmentation", "görüntü bölütleme", "optical character recognition", "OCR", "optik karakter tanıma", "video analysis", "video analizi", "pose estimation", "poz tahmini", "3D reconstruction", "3B yeniden yapılandırma"]
      },
      { 
        id: 104, 
        name: "Generatif Yapay Zeka",
        keywords: ["generative AI", "generative model", "üretici model", "text-to-image", "metinden görüntü", "diffusion model", "difüzyon modeli", "stable diffusion", "DALL-E", "Midjourney", "synthetic data", "sentetik veri", "content generation", "içerik üretimi", "creative AI", "yaratıcı yapay zeka", "multimodal", "çok kipli"]
      },
      { 
        id: 105, 
        name: "Makine Öğrenimi Algoritmaları",
        keywords: ["machine learning", "makine öğrenmesi", "supervised learning", "gözetimli öğrenme", "unsupervised learning", "gözetimsiz öğrenme", "reinforcement learning", "pekiştirmeli öğrenme", "clustering", "kümeleme", "classification", "sınıflandırma", "regression", "regresyon", "decision tree", "karar ağacı", "random forest", "rastgele orman", "SVM", "destek vektör makinesi", "boosting", "bagging", "ensemble learning", "topluluk öğrenmesi"]
      },
    ],
  },
  {
    id: 2,
    name: "İnsan-Bilgisayar Etkileşimi",
    icon: "👥",
    subcategories: [
      { 
        id: 201, 
        name: "Beyin-Bilgisayar Arayüzleri (BCI)",
        keywords: ["brain-computer interface", "beyin-bilgisayar arayüzü", "nöral arayüz", "neural interface", "EEG", "elektroensefalografi", "düşünce kontrolü", "thought control", "nöro-geri bildirim", "neurofeedback", "beyin sinyalleri", "brain signals", "nöroprostetik", "neuroprosthetics", "zihin-makine arabirimi", "mind-machine interface"]
      },
      { 
        id: 202, 
        name: "Kullanıcı Deneyimi Tasarımı",
        keywords: ["user experience", "UX design", "kullanıcı deneyimi", "kullanıcı arayüzü", "UI design", "kullanılabilirlik", "usability", "kullanıcı araştırması", "user research", "interaksiyon tasarımı", "interaction design", "wireframe", "tel çerçeve", "prototip", "prototype", "kullanıcı testi", "user testing", "kullanıcı merkezli tasarım", "user-centered design", "kişi", "persona", "kullanıcı yolculuğu", "user journey"]
      },
      { 
        id: 203, 
        name: "Artırılmış ve Sanal Gerçeklik (AR/VR)",
        keywords: ["augmented reality", "artırılmış gerçeklik", "virtual reality", "sanal gerçeklik", "mixed reality", "karma gerçeklik", "extended reality", "genişletilmiş gerçeklik", "VR", "AR", "XR", "immersive", "sürükleyici", "head-mounted display", "başa takılan ekran", "360 derece", "sanal ortam", "virtual environment", "metaverse", "metaevren", "spatial computing", "uzamsal hesaplama", "hologram", "holografi"]
      },
      { 
        id: 204, 
        name: "Etkileşim Tasarımı",
        keywords: ["interaction design", "etkileşim tasarımı", "gesture control", "hareket kontrolü", "touch interface", "dokunmatik arayüz", "voice interface", "ses arayüzü", "doğal kullanıcı arayüzü", "natural user interface", "NUI", "multimodal interaction", "çok kipli etkileşim", "gaze tracking", "bakış takibi", "haptic feedback", "dokunsal geri bildirim", "responsive design", "duyarlı tasarım", "adaptive interface", "uyarlanabilir arayüz"]
      },
      { 
        id: 205, 
        name: "Erişilebilirlik Teknolojileri",
        keywords: ["accessibility", "erişilebilirlik", "assistive technology", "yardımcı teknoloji", "evrensel tasarım", "universal design", "engelli kullanıcılar", "disabled users", "WCAG", "ekran okuyucu", "screen reader", "voice recognition", "ses tanıma", "color blindness", "renk körlüğü", "contrast", "kontrast", "keyboard navigation", "klavye navigasyonu", "alt text", "alternative text", "alternatif metin"]
      },
    ],
  },
  {
    id: 3,
    name: "Büyük Veri ve Veri Analitiği",
    icon: "📊",
    subcategories: [
      { 
        id: 301, 
        name: "Veri Madenciliği",
        keywords: ["data mining", "veri madenciliği", "pattern recognition", "örüntü tanıma", "feature extraction", "öznitelik çıkarımı", "anomaly detection", "anomali tespiti", "association rules", "birliktelik kuralları", "sequence mining", "dizi madenciliği", "veri keşfi", "data discovery", "text mining", "metin madenciliği", "web mining", "web madenciliği", "knowledge discovery", "bilgi keşfi"]
      },
      { 
        id: 302, 
        name: "Veri Görselleştirme",
        keywords: ["data visualization", "veri görselleştirme", "information visualization", "bilgi görselleştirme", "chart", "grafik", "dashboard", "gösterge paneli", "infographic", "bilgi grafiği", "interactive visualization", "etkileşimli görselleştirme", "visual analytics", "görsel analitik", "D3.js", "Tableau", "Power BI", "heatmap", "ısı haritası", "scatter plot", "dağılım grafiği", "treemap", "ağaç haritası"]
      },
      { 
        id: 303, 
        name: "Veri İşleme Sistemleri (Hadoop, Spark)",
        keywords: ["Hadoop", "Spark", "MapReduce", "HDFS", "distributed computing", "dağıtık hesaplama", "big data processing", "büyük veri işleme", "data lake", "veri gölü", "data warehouse", "veri ambarı", "batch processing", "toplu işleme", "stream processing", "akış işleme", "Kafka", "Flink", "Hive", "Pig", "NoSQL", "distributed file system", "dağıtık dosya sistemi"]
      },
      { 
        id: 304, 
        name: "Zaman Serisi Analizi",
        keywords: ["time series analysis", "zaman serisi analizi", "forecasting", "tahmin", "trend analysis", "trend analizi", "seasonality", "mevsimsellik", "ARIMA", "SARIMA", "exponential smoothing", "üstel düzleştirme", "temporal data", "zamansal veri", "time series forecasting", "zaman serisi tahmini", "autoregression", "otoregresyon", "temporal pattern", "zamansal örüntü", "change point detection", "değişim noktası tespiti"]
      },
      { 
        id: 305, 
        name: "Tahmine Dayalı Analizler",
        keywords: ["predictive analytics", "tahmine dayalı analitik", "predictive modeling", "tahmine dayalı modelleme", "forecasting", "öngörü", "business intelligence", "iş zekası", "risk analysis", "risk analizi", "customer analytics", "müşteri analitiği", "churn prediction", "müşteri kaybı tahmini", "propensity model", "eğilim modeli", "predictive maintenance", "öngörücü bakım", "market prediction", "pazar tahmini", "demand forecasting", "talep tahmini"]
      },
    ],
  },
  {
    id: 4,
    name: "Siber Güvenlik",
    icon: "🔒",
    subcategories: [
      { 
        id: 401, 
        name: "Şifreleme Algoritmaları",
        keywords: ["encryption", "şifreleme", "cryptography", "kriptografi", "cipher", "şifre", "hash", "hashing", "RSA", "AES", "symmetric encryption", "simetrik şifreleme", "asymmetric encryption", "asimetrik şifreleme", "public key", "açık anahtar", "private key", "özel anahtar", "digital signature", "dijital imza", "quantum cryptography", "kuantum kriptografi", "blockchain"]
      },
      { 
        id: 402, 
        name: "Güvenli Yazılım Geliştirme",
        keywords: ["secure coding", "güvenli kodlama", "secure SDLC", "güvenli yazılım geliştirme yaşam döngüsü", "code review", "kod incelemesi", "static analysis", "statik analiz", "dynamic analysis", "dinamik analiz", "vulnerability", "güvenlik açığı", "secure design", "güvenli tasarım", "threat modeling", "tehdit modellemesi", "penetration testing", "sızma testi", "security testing", "güvenlik testi", "secure DevOps", "DevSecOps"]
      },
      { 
        id: 403, 
        name: "Ağ Güvenliği",
        keywords: ["network security", "ağ güvenliği", "firewall", "güvenlik duvarı", "IDS", "intrusion detection", "sızma tespit", "IPS", "intrusion prevention", "sızma önleme", "VPN", "virtual private network", "sanal özel ağ", "DDoS", "denial of service", "hizmet reddi", "packet filtering", "paket filtreleme", "proxy", "vekil sunucu", "network monitoring", "ağ izleme", "secure routing", "güvenli yönlendirme"]
      },
      { 
        id: 404, 
        name: "Kimlik Doğrulama Sistemleri",
        keywords: ["authentication", "kimlik doğrulama", "authorization", "yetkilendirme", "multi-factor authentication", "çok faktörlü kimlik doğrulama", "biometric", "biyometrik", "passwordless", "şifresiz", "single sign-on", "tek oturum açma", "SSO", "identity management", "kimlik yönetimi", "OAuth", "SAML", "JWT", "zero trust", "sıfır güven", "identity provider", "kimlik sağlayıcı"]
      },
      { 
        id: 405, 
        name: "Adli Bilişim",
        keywords: ["digital forensics", "adli bilişim", "cyber forensics", "siber adli bilişim", "forensic analysis", "adli analiz", "evidence collection", "kanıt toplama", "incident response", "olay müdahale", "malware analysis", "zararlı yazılım analizi", "data recovery", "veri kurtarma", "chain of custody", "delil zinciri", "log analysis", "günlük analizi", "memory forensics", "bellek adli analizi", "disk imaging", "disk görüntüleme"]
      },
    ],
  },
  {
    id: 5,
    name: "Ağ ve Dağıtık Sistemler",
    icon: "🌐",
    subcategories: [
      { 
        id: 501, 
        name: "5G ve Yeni Nesil Ağlar",
        keywords: ["5G", "next-generation network", "yeni nesil ağ", "wireless", "kablosuz", "mobile network", "mobil ağ", "cellular", "hücresel", "network slicing", "ağ dilimleme", "edge computing", "uç hesaplama", "mmWave", "milimetre dalga", "beamforming", "ışın şekillendirme", "MIMO", "spectrum efficiency", "spektrum verimliliği", "ultra-reliable low latency", "ultra güvenilir düşük gecikme", "URLLC"]
      },
      { 
        id: 502, 
        name: "Bulut Bilişim",
        keywords: ["cloud computing", "bulut bilişim", "IaaS", "PaaS", "SaaS", "infrastructure as a service", "altyapı hizmeti", "platform as a service", "platform hizmeti", "software as a service", "yazılım hizmeti", "cloud storage", "bulut depolama", "cloud migration", "bulut geçişi", "virtualization", "sanallaştırma", "cloud security", "bulut güvenliği", "serverless", "sunucusuz", "hybrid cloud", "hibrit bulut", "multi-cloud", "çoklu bulut"]
      },
      { 
        id: 503, 
        name: "Blockchain Teknolojisi",
        keywords: ["blockchain", "blok zinciri", "distributed ledger", "dağıtık defter", "cryptocurrency", "kripto para", "Bitcoin", "Ethereum", "smart contract", "akıllı sözleşme", "consensus algorithm", "uzlaşma algoritması", "proof of work", "iş ispatı", "proof of stake", "hisse ispatı", "decentralized", "merkeziyetsiz", "DeFi", "merkeziyetsiz finans", "tokenization", "jetonlaştırma", "NFT", "non-fungible token", "değiştirilemez jeton"]
      },
      { 
        id: 504, 
        name: "P2P ve Merkeziyetsiz Sistemler",
        keywords: ["peer-to-peer", "eşler arası", "P2P", "decentralized systems", "merkeziyetsiz sistemler", "distributed", "dağıtık", "mesh network", "örgü ağ", "BitTorrent", "file sharing", "dosya paylaşımı", "distributed hash table", "dağıtık hash tablosu", "DHT", "decentralized applications", "merkeziyetsiz uygulamalar", "dApps", "distributed computing", "dağıtık hesaplama", "concurrent computing", "eşzamanlı hesaplama"]
      },
      { 
        id: 505, 
        name: "İnternet Protokolleri",
        keywords: ["internet protocols", "internet protokolleri", "IP", "TCP", "UDP", "HTTP", "HTTPS", "DNS", "DHCP", "IPv6", "routing protocol", "yönlendirme protokolü", "BGP", "OSPF", "network layer", "ağ katmanı", "transport layer", "taşıma katmanı", "application layer", "uygulama katmanı", "protocol stack", "protokol yığını", "REST", "API", "WebSocket"]
      },
    ],
  },
] 