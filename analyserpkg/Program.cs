using AssetStudio;
using System.Text;
using Object = AssetStudio.Object;

class Program
{
    static AssetsManager assetsManager = new ();
    static List<AssetItem> exportableAssets = new ();
    static string[] wrapModes = { "Repeat", "Clamp", "Mirror", "MirrorOnce", "Per-axis" };
    static string[] filterModes = { "Point", "Bilinear", "Trilinear" };
    static void Main(string[] args)
    {
        if(args.Length != 1) return;
        var path = args[0];
        if (Path.GetExtension(path).Equals(".apk"))
        {
            var unzipPath = path.Replace(".apk", "");
            if(Directory.Exists(unzipPath))
            {
                Directory.Delete(unzipPath, true);
            }
            Console.WriteLine($"UnZip {path}");
            System.IO.Compression.ZipFile.ExtractToDirectory(path, unzipPath);
            path = unzipPath;
        }
        if(Directory.Exists(path))
        {
            Console.WriteLine($"LoadFolder {path}");
            assetsManager.LoadFolder(path);

            Console.WriteLine("BuildAssetData");
            BuildAssetData();

            var pkgPath = $"{path}-pkg";
            Console.WriteLine($"ExportAssets {pkgPath}");
            if (!Directory.Exists(pkgPath))
                Directory.CreateDirectory(pkgPath);

            exportableAssets.Sort((x,y) => string.Compare(x.Text, y.Text));
            ExportAssets(pkgPath, exportableAssets);
        }
    }

    static bool ExportFile(AssetItem item, string savePath, StreamWriter csvFile)
    {
        bool result = true;
        string filename = "";
        string hash = "";
        string dimension = "";
        string format = "";
        string wrapMode = "";
        string filterMode = "";
        byte[] rawData = null;
        var sourcePath = savePath.Replace("-pkg", "\\");
        var exportPath = Path.Combine(savePath, item.TypeString);
        switch (item.Type)
        {
            case ClassIDType.Texture2D:
                {
                    var texture2D = (Texture2D)item.Asset;
                    if (texture2D.m_MipMap)
                        dimension = string.Format("{0}x{1} mips", texture2D.m_Width, texture2D.m_Height, texture2D.m_MipCount);
                    else
                        dimension = string.Format("{0}x{1}", texture2D.m_Width, texture2D.m_Height);
                    rawData = texture2D.image_data.GetData();
                    format = texture2D.m_TextureFormat.ToString();
                    wrapMode = $"U:{wrapModes[texture2D.m_TextureSettings.m_WrapMode]} V:{wrapModes[texture2D.m_TextureSettings.m_WrapV]} W:{wrapModes[texture2D.m_TextureSettings.m_WrapW]}";
                    filterMode = filterModes[texture2D.m_TextureSettings.m_FilterMode];
                    break;
                }
            case ClassIDType.Texture2DArray:
                {
                    rawData = item.Asset.GetRawData();
                    break;
                }
            case ClassIDType.Shader:
                {
                    rawData = item.Asset.GetRawData();
                    break;
                }
            case ClassIDType.Font:
                {
                    var font = (Font)item.Asset;
                    rawData = font.m_FontData;
                    break;
                }
            case ClassIDType.Mesh:
                {
                    var mesh = (Mesh)item.Asset;
                    rawData = item.Asset.GetRawData();
                    dimension = $"vtx:{mesh.m_VertexCount} idx:{mesh.m_Indices.Count} uv:{mesh.m_UV0?.Length} n:{mesh.m_Normals?.Length}";
                    break;
                }
            case ClassIDType.TextAsset:
                {
                    rawData = item.Asset.GetRawData();
                    break;
                }
            case ClassIDType.AudioClip:
                {
                    rawData = item.Asset.GetRawData();
                    var audioClip = (AudioClip)item.Asset;
                    break;
                }
            case ClassIDType.AnimationClip:
                {
                    rawData = item.Asset.GetRawData();
                    var animationClip = (AnimationClip)item.Asset;
                    break;
                }
            default:
                return false;
        }

        if (rawData != null)
        {
            using (System.Security.Cryptography.MD5 md5 = System.Security.Cryptography.MD5.Create())
            {
                byte[] retVal = md5.ComputeHash(rawData);
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < retVal.Length; i++)
                {
                    sb.Append(retVal[i].ToString("x2"));
                }
                hash = sb.ToString();
            }
        }
        item.Text = item.Text.Replace("\0", "");
        //csvFile.Write("Name,Container,Type,Dimension,Format,Size,FileName,Hash,OriginalFile\n");
        var originalFile = item.SourceFile.originalPath ?? item.SourceFile.fullName;
        originalFile = originalFile.Replace(sourcePath, "");
        originalFile = originalFile.Replace("\\", "/");
        csvFile.Write($"{item.Text}\t{item.Container}\t{item.TypeString}\t{dimension}\t{format}\t{item.FullSize}\t{filename}\t{hash}\t{originalFile}\t{wrapMode}\t{filterMode}\n");

        return result;
    }

    static void ExportAssets(string savePath, List<AssetItem> toExportAssets)
    {
        string csvFileName = Path.Combine(savePath, "pkg.tsv");
        var csvFile = new StreamWriter(csvFileName);
        csvFile.Write("Name\tContainer\tType\tDimension\tFormat\tSize\tFileName\tHash\tOriginalFile\tWrapMode\tFilterMode\n");
        int exportedCount = 0;
        foreach (var asset in toExportAssets)
        {
            Console.WriteLine($"Exporting {asset.TypeString}: {asset.Text}");
            try
            {
                if (ExportFile(asset, savePath, csvFile))
                {
                    exportedCount++;
                }
            }
            catch (Exception)
            {
            }
        }

        if (csvFile.BaseStream != null)
        {
            csvFile.Close();
        }
    }

    public class AssetItem
    {
        public string Text;
        public Object Asset;
        public SerializedFile SourceFile;
        public string Container = string.Empty;
        public string TypeString;
        public long FullSize;
        public ClassIDType Type;
        public string UniqueID;

        public AssetItem(Object asset)
        {
            Asset = asset;
            SourceFile = asset.assetsFile;
            Type = asset.type;
            TypeString = Type.ToString();
            FullSize = asset.byteSize;
        }
    }
    public static void BuildAssetData()
    {
        Console.WriteLine("Building asset list...");

        string productName = null;
        var objectCount = assetsManager.assetsFileList.Sum(x => x.Objects.Count);
        var objectAssetItemDic = new Dictionary<Object, AssetItem>(objectCount);
        var containers = new List<(PPtr<Object>, string)>();
        int i = 0;
        foreach (var assetsFile in assetsManager.assetsFileList)
        {
            foreach (var asset in assetsFile.Objects)
            {
                var assetItem = new AssetItem(asset);
                objectAssetItemDic.Add(asset, assetItem);
                assetItem.UniqueID = " #" + i;
                var exportable = false;
                switch (asset)
                {
                    case GameObject m_GameObject:
                        assetItem.Text = m_GameObject.m_Name;
                        break;
                    case Texture2D m_Texture2D:
                        if (!string.IsNullOrEmpty(m_Texture2D.m_StreamData?.path))
                            assetItem.FullSize = asset.byteSize + m_Texture2D.m_StreamData.size;
                        assetItem.Text = m_Texture2D.m_Name;
                        exportable = true;
                        break;
                    case AudioClip m_AudioClip:
                        if (!string.IsNullOrEmpty(m_AudioClip.m_Source))
                            assetItem.FullSize = asset.byteSize + m_AudioClip.m_Size;
                        assetItem.Text = m_AudioClip.m_Name;
                        exportable = true;
                        break;
                    case VideoClip m_VideoClip:
                        if (!string.IsNullOrEmpty(m_VideoClip.m_OriginalPath))
                            assetItem.FullSize = asset.byteSize + (long)m_VideoClip.m_ExternalResources.m_Size;
                        assetItem.Text = m_VideoClip.m_Name;
                        exportable = true;
                        break;
                    case Shader m_Shader:
                        assetItem.Text = m_Shader.m_ParsedForm?.m_Name ?? m_Shader.m_Name;
                        exportable = true;
                        break;
                    case Mesh _:
                    case TextAsset _:
                    case AnimationClip _:
                    case Font _:
                    case MovieTexture _:
                    case Sprite _:
                        assetItem.Text = ((NamedObject)asset).m_Name;
                        exportable = true;
                        break;
                    case Animator m_Animator:
                        if (m_Animator.m_GameObject.TryGet(out var gameObject))
                        {
                            assetItem.Text = gameObject.m_Name;
                        }
                        exportable = true;
                        break;
                    case MonoBehaviour m_MonoBehaviour:
                        if (m_MonoBehaviour.m_Name == "" && m_MonoBehaviour.m_Script.TryGet(out var m_Script))
                        {
                            assetItem.Text = m_Script.m_ClassName;
                        }
                        else
                        {
                            assetItem.Text = m_MonoBehaviour.m_Name;
                        }
                        exportable = true;
                        break;
                    case PlayerSettings m_PlayerSettings:
                        productName = m_PlayerSettings.productName;
                        break;
                    case AssetBundle m_AssetBundle:
                        foreach (var m_Container in m_AssetBundle.m_Container)
                        {
                            var preloadIndex = m_Container.Value.preloadIndex;
                            var preloadSize = m_Container.Value.preloadSize;
                            var preloadEnd = preloadIndex + preloadSize;
                            for (int k = preloadIndex; k < preloadEnd; k++)
                            {
                                containers.Add((m_AssetBundle.m_PreloadTable[k], m_Container.Key));
                            }
                        }
                        assetItem.Text = m_AssetBundle.m_Name;
                        break;
                    case ResourceManager m_ResourceManager:
                        foreach (var m_Container in m_ResourceManager.m_Container)
                        {
                            containers.Add((m_Container.Value, m_Container.Key));
                        }
                        break;
                    case NamedObject m_NamedObject:
                        assetItem.Text = m_NamedObject.m_Name;
                        break;
                }
                if (assetItem.Text == "")
                {
                    assetItem.Text = assetItem.TypeString + assetItem.UniqueID;
                }
                if (exportable)
                {
                    exportableAssets.Add(assetItem);
                }
                ++i;
            }
        }
        foreach ((var pptr, var container) in containers)
        {
            if (pptr.TryGet(out var obj))
            {
                objectAssetItemDic[obj].Container = container;
            }
        }
    }
}