using System.Reflection;
using System.Runtime.Loader;
using System.Runtime.InteropServices;

var engineDir = args.Length > 0
    ? Path.GetFullPath(args[0])
    : @"C:\Program Files (x86)\Flax\Flax_1.12\Binaries\Editor\Win64\Development";

var alc = new AssemblyLoadContext("probe", isCollectible: false);
alc.Resolving += (ctx, name) =>
{
    var candidate = Path.Combine(engineDir, name.Name + ".dll");
    return File.Exists(candidate) ? ctx.LoadFromAssemblyPath(candidate) : null;
};

var flax = alc.LoadFromAssemblyPath(Path.Combine(engineDir, "FlaxEngine.CSharp.dll"));
Console.WriteLine($"Loaded {flax.FullName}");
Console.WriteLine();

var netTypes = flax.GetTypes().Where(t => (t.Namespace ?? "").StartsWith("FlaxEngine.Networking"))
    .OrderBy(t => t.FullName).ToArray();
Console.WriteLine("== FlaxEngine.Networking types ==");
foreach (var t in netTypes) Console.WriteLine("  " + t.FullName);
Console.WriteLine();

var msgType = flax.GetType("FlaxEngine.Networking.NetworkMessage");
Console.WriteLine("== NetworkMessage members ==");
foreach (var m in msgType.GetMembers(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly)
    .Where(m => m.MemberType is MemberTypes.Method or MemberTypes.Constructor or MemberTypes.Field or MemberTypes.Property))
{
    switch (m)
    {
        case MethodInfo mi:
            Console.WriteLine($"  M {mi.ReturnType.Name} {mi.Name}({(string.Join(",", mi.GetParameters().Select(p => p.ParameterType.Name)))}) [{(mi.IsPublic ? "pub" : "nonpub")}]");
            break;
        case FieldInfo fi:
            Console.WriteLine($"  F {fi.FieldType.Name} {fi.Name}");
            break;
        case PropertyInfo pi:
            Console.WriteLine($"  P {pi.PropertyType.Name} {pi.Name}");
            break;
        case ConstructorInfo ci:
            Console.WriteLine($"  C .ctor({(string.Join(",", ci.GetParameters().Select(p => p.ParameterType.Name)))}) [{(ci.IsPublic ? "pub" : "nonpub")}]");
            break;
    }
}
Console.WriteLine();

var isValueType = msgType.IsValueType;
Console.WriteLine($"NetworkMessage IsValueType={isValueType}");
Console.WriteLine();

object Make()
{
    if (isValueType)
        return Activator.CreateInstance(msgType)!;
    var ctor = msgType.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance).FirstOrDefault();
    if (ctor == null) throw new InvalidOperationException("no ctor");
    return ctor.Invoke(ctor.GetParameters().Length == 0 ? Array.Empty<object>() : new object?[ctor.GetParameters().Length].ToArray()!);
}

string HexDump(object msg)
{
    var buffer = (IntPtr)msgType.GetField("Buffer", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance)!.GetValue(msg)!;
    var length = (uint)msgType.GetField("Length", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance)!.GetValue(msg)!;
    if (buffer == IntPtr.Zero) return "(null buffer)";
    var bytes = new byte[length];
    Marshal.Copy(buffer, bytes, 0, (int)length);
    return BitConverter.ToString(bytes);
}

void Probe(string label, Action<object> write)
{
    try
    {
        var msg = Make();
        write(msg);
        Console.WriteLine($"  {label}: {HexDump(msg)}");
    }
    catch (Exception ex)
    {
        var inner = ex.InnerException;
        var detail = inner != null ? $"{inner.GetType().Name}: {inner.Message}" : $"{ex.GetType().Name}: {ex.Message}";
        Console.WriteLine($"  {label}: EXCEPTION {detail}");
    }
}

Console.WriteLine();
Console.WriteLine("== P/Invoke check ==");
var wb = msgType.GetMethod("WriteByte")!;
Console.WriteLine($"  WriteByte IsPInvoke={wb.Attributes.HasFlag(MethodAttributes.PinvokeImpl)} HasBody={TryBody(wb)}");
var ws = msgType.GetMethod("WriteString")!;
Console.WriteLine($"  WriteString IsPInvoke={ws.Attributes.HasFlag(MethodAttributes.PinvokeImpl)} HasBody={TryBody(ws)}");
var wi = msgType.GetMethod("WriteInt32")!;
Console.WriteLine($"  WriteInt32 IsPInvoke={wi.Attributes.HasFlag(MethodAttributes.PinvokeImpl)} HasBody={TryBody(wi)}");
foreach (var mi in new[] { wb, ws, wi })
{
    var dll = mi.GetCustomAttributesData().FirstOrDefault(a => a.AttributeType.Name == "DllImportAttribute");
    if (dll != null)
    {
        var ctorArgs = string.Join(", ", dll.ConstructorArguments.Select(a => a.Value));
        var namedArgs = string.Join(", ", dll.NamedArguments.Select(a => $"{a.MemberName}={a.TypedValue.Value}"));
        Console.WriteLine($"  {mi.Name} DllImport({ctorArgs}) [{namedArgs}]");
    }
}

string TryBody(MethodInfo mi)
{
    try
    {
        var body = mi.GetMethodBody();
        if (body == null) return "false (null)";
        var il = body.GetILAsByteArray();
        return $"true ({il.Length} il bytes, maxStack={body.MaxStackSize})";
    }
    catch (InvalidOperationException)
    {
        return "false (no body)";
    }
}

Console.WriteLine();
Console.WriteLine("== Fabricated-buffer probes ==");

var vec3 = flax.GetType("FlaxEngine.Vector3")!;
var vec3Ctor = vec3.GetConstructors().First(c => c.GetParameters().Length == 3);
var v3 = vec3Ctor.Invoke(new object[] { 1f, 2f, 3f });

var quat = flax.GetType("FlaxEngine.Quaternion")!;
var quatCtor = quat.GetConstructors().First(c => c.GetParameters().Length == 4);
var q = quatCtor.Invoke(new object[] { 0.5f, 0.5f, 0.5f, 0.5f });

var boxed = Activator.CreateInstance(msgType)!;
var bufField = msgType.GetField("Buffer", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance)!;
var lenField = msgType.GetField("Length", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance)!;
var posField = msgType.GetField("Position", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance)!;
var sizeField = msgType.GetField("BufferSize", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance)!;

var raw = new byte[16384];
var pin = GCHandle.Alloc(raw, GCHandleType.Pinned);
try
{
    bufField.SetValue(boxed, pin.AddrOfPinnedObject());
    sizeField.SetValue(boxed, (uint)raw.Length);
    lenField.SetValue(boxed, 0u);
    posField.SetValue(boxed, 0u);

    object Current() => boxed;

    void Probe2(string label, Action<object> write)
    {
        try
        {
            var m = Current();
            lenField.SetValue(m, 0u);
            posField.SetValue(m, 0u);
            write(m);
            var length = (uint)lenField.GetValue(m)!;
            var bytes = new byte[length];
            Array.Copy(raw, bytes, (int)length);
            Console.WriteLine($"  {label}: {BitConverter.ToString(bytes)}");
        }
        catch (Exception ex)
        {
            var inner = ex.InnerException;
            var detail = inner != null ? $"{inner.GetType().Name}: {inner.Message}" : $"{ex.GetType().Name}: {ex.Message}";
            Console.WriteLine($"  {label}: EXCEPTION {detail}");
        }
    }

    Probe2("WriteByte(0xAB)", m => m.GetType().GetMethod("WriteByte")!.Invoke(m, new object[] { (byte)0xAB }));
    Probe2("WriteInt32(-1)", m => m.GetType().GetMethod("WriteInt32")!.Invoke(m, new object[] { -1 }));
    Probe2("WriteInt32(300)", m => m.GetType().GetMethod("WriteInt32")!.Invoke(m, new object[] { 300 }));
    Probe2("WriteUInt32(4294967295)", m => m.GetType().GetMethod("WriteUInt32")!.Invoke(m, new object[] { uint.MaxValue }));
    Probe2("WriteInt64(-2)", m => m.GetType().GetMethod("WriteInt64")!.Invoke(m, new object[] { -2L }));
    Probe2("WriteInt16(-3)", m => m.GetType().GetMethod("WriteInt16")!.Invoke(m, new object[] { (short)-3 }));
    Probe2("WriteBoolean(true)", m => m.GetType().GetMethod("WriteBoolean")!.Invoke(m, new object[] { true }));
    Probe2("WriteBoolean(false)", m => m.GetType().GetMethod("WriteBoolean")!.Invoke(m, new object[] { false }));
    Probe2("WriteSingle(1.5)", m => m.GetType().GetMethod("WriteSingle")!.Invoke(m, new object[] { 1.5f }));
    Probe2("WriteString(\"Hi\")", m => m.GetType().GetMethod("WriteString")!.Invoke(m, new object[] { "Hi" }));
    Probe2("WriteString(\"\")", m => m.GetType().GetMethod("WriteString")!.Invoke(m, new object[] { "" }));
    Probe2("WriteString(\"café\")", m => m.GetType().GetMethod("WriteString")!.Invoke(m, new object[] { "café" }));
    Probe2("WriteString(300x'a')", m => m.GetType().GetMethod("WriteString")!.Invoke(m, new object[] { new string('a', 300) }));
    Probe2("WriteString(256x'a')", m => m.GetType().GetMethod("WriteString")!.Invoke(m, new object[] { new string('a', 256) }));
    Probe2("WriteString(257x'a')", m => m.GetType().GetMethod("WriteString")!.Invoke(m, new object[] { new string('a', 257) }));
    Probe2("WriteGuid(01234567-89ab-cdef-0123-456789abcdef)", m => m.GetType().GetMethod("WriteGuid")!.Invoke(m, new object[] { Guid.Parse("01234567-89ab-cdef-0123-456789abcdef") }));
    Probe2("WriteGuid(ffffffff-ffff-ffff-ffff-ffffffffffff)", m => m.GetType().GetMethod("WriteGuid")!.Invoke(m, new object[] { Guid.Parse("ffffffff-ffff-ffff-ffff-ffffffffffff") }));

    Probe2("WriteVector3(1,2,3) [typed]", m => m.GetType().GetMethod("WriteVector3")!.Invoke(m, new object[] { v3 }));
    Probe2("WriteQuaternion(0.5x4)", m => m.GetType().GetMethod("WriteQuaternion")!.Invoke(m, new object[] { q }));
    Probe2("WriteBytes(01 02 03, 3)", m => m.GetType().GetMethod("WriteBytes", new[] { typeof(byte[]), typeof(int) })!.Invoke(m, new object[] { new byte[] { 1, 2, 3 }, 3 }));
    Probe2("WriteBytes(null, 0)", m => m.GetType().GetMethod("WriteBytes", new[] { typeof(byte[]), typeof(int) })!.Invoke(m, new object[] { null, 0 }));

    Console.WriteLine();
    Console.WriteLine("== Read-back sanity (Deserialize path) ==");
    var readMsg = Current();
    lenField.SetValue(readMsg, 0u);
    posField.SetValue(readMsg, 0u);
    var wt = readMsg.GetType().GetMethod("WriteString")!;
    var rd = readMsg.GetType().GetMethod("ReadString")!;
    wt.Invoke(readMsg, new object[] { "Hello" });
    var got = rd.Invoke(readMsg, null);
    Console.WriteLine($"  ReadString after WriteString(\"Hello\") -> '{got}'");
}
finally
{
    pin.Free();
}

Console.WriteLine();
Console.WriteLine("DONE");
return 0;
