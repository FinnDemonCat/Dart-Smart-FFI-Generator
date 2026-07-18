# C Struct to Dart FFI Binding Generator

Semi automatic Python script, built arround raylib C library code style conventions into Dart classes. Tailored for [Target]("https://github.com/FinnDemonCat/Target") Dart bindings project.

---

## 🛠 How to Prepare the Input File

The script takes only one input type. Firstly it reads `native_code_input.c.txt` and searches for the struct typedef, followed by the `# Constructor` tag, the `# Named Constructor` tag, the `# Methods` tag and finally the `# Deconstructor` tag:

1. **`typedef struct`**: The target C structure definition.
2. **`# Constructor`**: Defines functions that return a new instance of the struct (maps to the default Dart constructor).
3. **`# Named Constructor`**: Defines functions that return a new instance but map to Dart named constructors (e.g., `Image.fromMemory()`).
4. **`# Methods`**: Functions where the instance itself is passed around.
5. **`# Deconstructor`**: Functions meant to free up native memory resources.

---

## 📋 Input Specifications Example

Save your C header configurations like the example below (e.g., `native_code_input.c.txt`):

```c
// Image, pixel data stored in CPU memory (RAM)
typedef struct Image {
    void *data;             // Image raw data
    int width;              // Image base width
    int height;             // Image base height
    int mipmaps;            // Mipmap levels, 1 by default
    int format;             // Data format (PixelFormat type)
} Image;

# Constructor (New return instance)
Image LoadImage(const char *fileName);

# Named Constructor (New return instance)
Image LoadImageRaw(const char *fileName, int width, int height, int format, int headerSize);
Image LoadImageAnim(const char *fileName, int *frames);
Image LoadImageFromMemory(const char *fileType, const unsigned char *fileData, int dataSize);

# Methods (Assumes first parameter is the class instance)
bool IsImageValid(Image image);
void ImageClearBackground(Image *dst, Color color);
void ImageDrawPixel(Image *dst, int posX, int posY, Color color);

# Deconstructor
void UnloadImage(Image image);
```

## ⚙️ Generation Conventions
### 1. Method Binding (Parameter Hiding)

When a function is listed under Methods, the generator assumes that the first parameter is always the reference to the current instance.
- In C: void ImageClearBackground(Image *dst, Color color);
- In Dart: It becomes an extension/member method .clearBackground(Color color), automatically passing `this` behind the scenes.

### Ex:
```c
C:
// Clear image background with given color
void ImageClearBackground(Image *dst, Color color);

Dart:
/// Clear image background with given color
void ClearBackground(Color color) => _imageClearBackground(pointer, color.ref);
```

### 2. Constructor Conversion

- Default Constructor: Functions under `# Constructor` match the structure name directly (e.g., LoadImage $\rightarrow$ Image()).

- Named Constructors: tries to replace any match of the struct name in the function name (e.g., LoadImageRaw $\rightarrow$ Image.LoadRaw()).

- Deconstructors / FinalizersFunctions listed under `# Deconstructor` are wrapped into custom Free C handles receiving a void* pointer, safely mapping memory release mechanisms for Dart's native garbage collection lifecycle management.

## ⚙️ NativeWrapper class
NativeWrapper its a simple class created as a template for all these classes that wrap pointer instance of that struct.

```dart
/// A base utility class designed to manage the lifecycle and allocation 
/// of native C memory resources through Dart FFI.
///
/// It acts as a wrapper around raw pointers, ensuring safe memory deallocation
/// and preventing memory leaks.
class NativeWrapper<T extends NativeType> {
  /// The raw physical address pointer pointing to the native heap memory.
  final Pointer<T> pointer;
  /// The number of sequential elements of type [T] allocated in memory (useful for arrays).
  final int length;

  bool _disposed = false;
  /// Indicates whether the native memory has already been deallocated.
  bool get IsDisposed => _disposed;
  /// Determines if this Dart instance is responsible for freeing the native memory.
  /// 
  /// If `true`, the memory will be released when [Free] is called. If `false`, 
  /// the memory is treated as an external reference managed elsewhere.
  bool IsOwner = true;

  /// An iterable helper getter set as a standard for the user to implement
  /// the necessary iterator when the pointer acts as an array
  Iterable<NativeWrapper<T>> get values => [this];

  /// Default constructor that allocates a fresh block of native memory on the C heap.
  /// 
  /// The total size allocated is calculated as `size * length`.
  NativeWrapper(int size,{ this.IsOwner = true, this.length = 1, RaylibArena? arena }) :
    pointer = malloc.allocate<T>(size * length) {
    if (IsOwner) arena?.register(this);
  }
  
  /// Alternative constructor to wrap an existing native pointer without reallocating memory.
  /// 
  /// Defaults [IsOwner] to `false` to prevent accidental double-free bugs.
  NativeWrapper.fromAddress(Pointer<T> pointer,{ this.IsOwner = false, this.length = 1, RaylibArena? arena }) :
    pointer = .fromAddress(pointer.address) {
    if (IsOwner) arena?.register(this);
  }

  // Direct call to [arena] to register [this] to be freed 
  void register(RaylibArena arena) => arena.register(this);

  /// Releases the allocated native memory associated with [pointer].
  /// 
  /// This operation will only execute if the object is the [IsOwner] and 
  /// has not been [IsDisposed] yet.
  @mustCallSuper
  void Free() {
    if (IsDisposed)
      return;
    if (!IsOwner)
      return;
    
    _disposed = true;
    malloc.free(this.pointer);
  }
}
```