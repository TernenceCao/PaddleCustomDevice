// Copyright (c) 2024 PaddlePaddle Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once
#include <string>
#include <vector>

#include "common/host_pinned_allocator.h"
#include "paddle/phi/common/data_type.h"
#include "runtime/runtime.h"

namespace custom_kernel {
// using Tensor = phi::DenseTensor;
// using Context = phi::CustomContext;
// using DataType = phi::DataType;
// using DataLayout = phi::DataLayout;
/**
 * CPU -> GCU
 * GCU -> CPU
 * GCU -> GCU
 */

template <typename Context>
inline void TensorCopy(const Context& dev_ctx,
                       const phi::DenseTensor& src,
                       bool blocking,
                       phi::DenseTensor* dst,
                       const phi::Place& dst_place = phi::CustomPlace()) {
  auto* src_ptr = src.data();
  const auto& src_place = src.place();
  if (src_ptr == nullptr) {
    return;
  }
  auto dst_place_ = dst_place;
  if (dst_place_.GetType() != phi::AllocationType::CPU) {
    dst_place_ = dev_ctx.GetPlace();
  }

  if (&src == dst) {
    if (src_place == dst_place_) {
      VLOG(6) << "Skip copy the same data(" << src_ptr << ") from " << src_place
              << " to " << dst_place_;
    } else {
      VLOG(6) << "Src and dst are the same Tensor, in-place copy data("
              << src_ptr << ") from " << src_place << " to " << dst_place_;
      const phi::DenseTensor src_copy = src;
      TensorCopy(dev_ctx, src_copy, blocking, dst, dst_place_);
    }
    return;
  }

  auto dst_dims = dst->dims();
  dst->Resize(src.dims());
  void* dst_ptr = nullptr;
  if (dst_place_.GetType() != phi::AllocationType::CPU) {
    dst_ptr = dev_ctx.Alloc(dst, src.dtype());
  } else {
    dst_ptr = dev_ctx.HostAlloc(dst, src.dtype());
  }

  PADDLE_ENFORCE_EQ(
      dst->place(),
      dst_place_,
      phi::errors::Unavailable(
          "The Dst Tensor's place and dst_place do not match, Tensor's place "
          "place is %s, dst_place is %s.",
          dst->place(),
          dst_place_));

  if (src_ptr == dst_ptr && src_place == dst_place_) {
    if ((dst_dims == src.dims()) || (src_place == phi::CPUPlace())) {
      VLOG(3) << "Skip copy the same data async from " << src_ptr << " in "
              << src_place << " to " << dst_ptr << " in " << dst_place_;
      return;
    } else {
      // scatter memory
      phi::DenseTensor tmp_dst;
      tmp_dst.set_meta(dst->meta());
      tmp_dst.Resize(dst_dims);
      dst_ptr = dev_ctx.Alloc(&tmp_dst, tmp_dst.dtype());
      *dst = tmp_dst;
    }
  }
  VLOG(4) << "src:" << src_ptr << " place: " << src_place
          << " type:" << static_cast<int>(src_place.GetType())
          << ", dst:" << dst_ptr << " place: " << dst_place_
          << " type:" << static_cast<int>(dst_place_.GetType());

  C_Stream stream = static_cast<C_Stream>(dev_ctx.stream());

  auto size =
      (src.dims().size() != 0 ? src.numel() : 1) * phi::SizeOf(src.dtype());
  if (UNLIKELY(size) == 0) {
    return;
  }

  if (src_place.GetType() == phi::AllocationType::CPU &&
      dst_place_.GetType() == phi::AllocationType::CUSTOM) {
    VLOG(6) << "TensorCopy from cpu to cus";
    C_Device_st device;
    device.id = dst_place_.GetDeviceId();
    AsyncMemCpyH2D(&device, stream, dst_ptr, src_ptr, size);
    if (blocking) {
      dev_ctx.Wait();
    }
  } else if (src_place.GetType() == phi::AllocationType::CUSTOM &&
             dst_place_.GetType() == phi::AllocationType::CPU) {
    VLOG(6) << "TensorCopy from cus to cpu";
    C_Device_st device;
    device.id = src_place.GetDeviceId();
    AsyncMemCpyD2H(&device, stream, dst_ptr, src_ptr, size);
    if (blocking) {
      dev_ctx.Wait();
    }
  } else if (src_place.GetType() == phi::AllocationType::CUSTOM &&
             dst_place_.GetType() == phi::AllocationType::CUSTOM) {
    VLOG(6) << "TensorCopy from cus to cus";
    if (src_place.GetDeviceType() == dst_place_.GetDeviceType()) {
      if (src_place.GetDeviceId() == dst_place_.GetDeviceId()) {
        C_Device_st device;
        device.id = src_place.GetDeviceId();
        AsyncMemCpyD2D(&device, stream, dst_ptr, src_ptr, size);
        if (blocking) {
          dev_ctx.Wait();
        }
      } else {
        PADDLE_THROW(
            phi::errors::Unimplemented("TensorCopy is not supported."));
      }
    } else {
      PADDLE_THROW(phi::errors::Unimplemented("TensorCopy is not supported."));
    }
  } else if (src_place.GetType() == phi::AllocationType::CPU &&
             dst_place_.GetType() == phi::AllocationType::CPU) {
    VLOG(6) << "TensorCopy from cpu to cpu";
    std::memcpy(dst_ptr, src_ptr, size);
  }
}

/**
 * CPU -> GCU
 */
template <typename T>
inline void TensorFromValue(const phi::CustomContext& ctx,
                            const T& src,
                            const phi::CustomContext& dev_ctx,
                            phi::DenseTensor* dst) {
  auto dst_place = dev_ctx.GetPlace();
  auto src_ptr = static_cast<const void*>(&src);
  dst->Resize(phi::make_ddim({}));
  auto dst_ptr = static_cast<void*>(dev_ctx.template Alloc<T>(dst));
  auto size = sizeof(T);
  if (UNLIKELY(size == 0)) return;

  if (dst_place.GetType() == phi::AllocationType::CUSTOM) {
    C_Device_st device;
    device.id = dst_place.GetDeviceId();
    AsyncMemCpyH2D(&device,
                   static_cast<C_Stream>(dev_ctx.stream()),
                   dst_ptr,
                   src_ptr,
                   size);
  } else {
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorFromValue on %s is not supported.", dst_place));
  }
}

template <>
inline void TensorFromValue<bool>(const phi::CustomContext& ctx,
                                  const bool& src,
                                  const phi::CustomContext& dev_ctx,
                                  phi::DenseTensor* dst) {
  // vector<bool> has no data() member, use array instead.
  // See details:
  // https://stackoverflow.com/questions/46115669/why-does-stdvectorbool-have-no-data/46115714

  auto dst_place = dev_ctx.GetPlace();
  auto src_ptr = static_cast<const void*>(&src);
  dst->Resize(phi::make_ddim({}));
  auto dst_ptr = static_cast<void*>(dev_ctx.template Alloc<bool>(dst));
  auto size = sizeof(bool);
  if (UNLIKELY(size == 0)) return;

  if (dst_place.GetType() == phi::AllocationType::CUSTOM) {
    C_Device_st device;
    device.id = dst_place.GetDeviceId();
    AsyncMemCpyH2D(&device,
                   static_cast<C_Stream>(dev_ctx.stream()),
                   dst_ptr,
                   src_ptr,
                   size);
  } else {
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorFromValue on %s is not supported.", dst_place));
  }
  // Destruction of temporary variables needs to wait for
  // the completion of the H2D copy.
  dev_ctx.Wait();
}

/**
 * CPU -> GCU
 */
template <typename T>
inline void TensorFromVector(
    const phi::CustomContext& ctx,
    const std::vector<T, PinnedAllocatorForSTL<T>>& src,
    const phi::CustomContext& dev_ctx,
    phi::DenseTensor* dst) {
  auto dst_place = dev_ctx.GetPlace();
  auto src_ptr = static_cast<const void*>(src.data());
  dst->Resize({static_cast<int64_t>(src.size())});
  auto dst_ptr = static_cast<void*>(dev_ctx.template Alloc<T>(dst));
  auto size = src.size() * sizeof(T);
  if (UNLIKELY(size == 0)) return;

  if (dst_place.GetType() == phi::AllocationType::CUSTOM) {
    C_Device_st device;
    device.id = dst_place.GetDeviceId();
    AsyncMemCpyH2D(&device,
                   static_cast<C_Stream>(dev_ctx.stream()),
                   dst_ptr,
                   src_ptr,
                   size);
  } else {
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorFromVector on %s is not supported.", dst_place));
  }
}

template <>
inline void TensorFromVector<bool>(
    const phi::CustomContext& ctx,
    const std::vector<bool, PinnedAllocatorForSTL<bool>>& src,
    const phi::CustomContext& dev_ctx,
    phi::DenseTensor* dst) {
  PADDLE_THROW(phi::errors::Unimplemented(
      "TensorFromVector for pinned bool is not supported."));
}

/**
 * CPU -> GCU
 */
template <typename T>
inline void TensorFromVector(const phi::CustomContext& ctx,
                             const std::vector<T>& src,
                             const phi::CustomContext& dev_ctx,
                             phi::DenseTensor* dst) {
  std::vector<T, PinnedAllocatorForSTL<T>> src_pinned(src.begin(), src.end());
  TensorFromVector<T>(ctx, src_pinned, dev_ctx, dst);
}

template <>
inline void TensorFromVector<bool>(const phi::CustomContext& ctx,
                                   const std::vector<bool>& src,
                                   const phi::CustomContext& dev_ctx,
                                   phi::DenseTensor* dst) {
  // vector<bool> has no data() member, use array instead.
  // See details:
  // https://stackoverflow.com/questions/46115669/why-does-stdvectorbool-have-no-data/46115714
  bool* array = new bool[src.size()];
  for (unsigned int i = 0; i < src.size(); i++) {
    array[i] = static_cast<bool>(src[i]);
  }

  auto dst_place = dev_ctx.GetPlace();
  auto src_ptr = static_cast<const void*>(array);
  dst->Resize({static_cast<int64_t>(src.size())});
  auto dst_ptr = static_cast<void*>(dev_ctx.template Alloc<bool>(dst));
  auto size = src.size() * sizeof(bool);
  if (UNLIKELY(size == 0)) return;

  if (dst_place.GetType() == phi::AllocationType::CUSTOM) {
    C_Device_st device;
    device.id = dst_place.GetDeviceId();
    AsyncMemCpyH2D(&device,
                   static_cast<C_Stream>(dev_ctx.stream()),
                   dst_ptr,
                   src_ptr,
                   size);
  } else {
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorFromVector on %s is not supported.", dst_place));
  }
  // Destruction of temporary variables needs to wait for
  // the completion of the H2D copy.
  dev_ctx.Wait();
  delete[] array;
}

/**
 * CPU -> CPU
 * CPU -> GCU
 */
template <typename T>
inline void TensorFromVector(const phi::CustomContext& ctx,
                             const std::vector<T>& src,
                             const phi::CPUContext& dev_ctx,
                             phi::DenseTensor* dst) {
  auto dst_place = dev_ctx.GetPlace();
  auto src_ptr = static_cast<const void*>(src.data());
  dst->Resize({src.size()});
  auto size = src.size() * sizeof(T);
  if (UNLIKELY(size == 0)) {
    return;
  }

  if (dst_place.GetType() == phi::AllocationType::CPU) {
    auto dst_ptr = ctx.template HostAlloc<T>(dst);
    VLOG(4) << "src_ptr: " << src_ptr << ", dst_ptr: " << dst_ptr
            << ", size: " << size;
    std::memcpy(dst_ptr, src_ptr, size);
  } else {
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorFromVector on %s is not supported.", dst_place));
  }
}

template <>
inline void TensorFromVector<bool>(const phi::CustomContext& ctx,
                                   const std::vector<bool>& src,
                                   const phi::CPUContext& dev_ctx,
                                   phi::DenseTensor* dst) {
  auto dst_place = dev_ctx.GetPlace();
  PADDLE_THROW(phi::errors::Unimplemented(
      "TensorFromVector for bool on %s is not supported.", dst_place));
}

template <typename T>
inline void TensorFromArray(const phi::CustomContext& ctx,
                            const T* src,
                            const size_t& array_size,
                            const phi::CustomContext& dev_ctx,
                            phi::DenseTensor* dst) {
  auto dst_place = dev_ctx.GetPlace();
  auto src_ptr = static_cast<const void*>(src);
  dst->Resize({static_cast<int64_t>(array_size)});
  auto dst_ptr = static_cast<void*>(dev_ctx.template Alloc<T>(dst));
  auto size = array_size * sizeof(T);

  if (dst_place.GetType() == phi::AllocationType::CUSTOM) {
    C_Device_st device;
    device.id = dst_place.GetDeviceId();
    AsyncMemCpyH2D(&device,
                   static_cast<C_Stream>(dev_ctx.stream()),
                   dst_ptr,
                   src_ptr,
                   size);
  } else {  // NOLINT
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorFromArray on %s is not supported.", dst_place));
  }
}

/**
 * GCU -> CPU
 */
template <typename T>
inline void TensorToVector(const phi::CustomContext& ctx,
                           const phi::DenseTensor& src,
                           const phi::CustomContext& dev_ctx,
                           std::vector<T>* dst) {
  auto src_ptr = static_cast<const void*>(src.data<T>());
  auto size = src.numel() * sizeof(T);

  dst->resize(src.numel());
  auto dst_ptr = static_cast<void*>(dst->data());

  auto src_place = src.place();

  if (src_place.GetType() == phi::AllocationType::CUSTOM) {
    C_Device_st device;
    device.id = src_place.GetDeviceId();
    AsyncMemCpyD2H(&device,
                   static_cast<C_Stream>(dev_ctx.stream()),
                   dst_ptr,
                   src_ptr,
                   size);
    ctx.Wait();
  } else {
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorToVector on %s is not supported.", src_place));
  }
}

template <>
inline void TensorToVector<bool>(const phi::CustomContext& ctx,
                                 const phi::DenseTensor& src,
                                 const phi::CustomContext& dev_ctx,
                                 std::vector<bool>* dst) {
  auto src_ptr = static_cast<const void*>(src.data<bool>());
  C_Stream stream = static_cast<C_Stream>(ctx.stream());
  auto size = src.numel() * sizeof(bool);

  bool* array = new bool[src.numel()];

  phi::CPUPlace dst_place;
  dst->resize(src.numel());
  auto dst_ptr = static_cast<void*>(array);

  auto src_place = src.place();
  if (src_place.GetType() == phi::AllocationType::CUSTOM) {
    C_Device_st device;
    device.id = src_place.GetDeviceId();
    AsyncMemCpyD2H(&device,
                   static_cast<C_Stream>(dev_ctx.stream()),
                   dst_ptr,
                   src_ptr,
                   size);
    ctx.Wait();
  } else {
    PADDLE_THROW(phi::errors::Unimplemented(
        "TensorToVector on %s is not supported.", src_place));
  }
  for (unsigned int i = 0; i < src.numel(); i++) {
    (*dst)[i] = static_cast<bool>(array[i]);
  }
  delete[] array;
}

inline int CanonicalAxis(const int axis, const int rank) {
  if (axis < 0) {
    return axis + rank;
  }
  return axis;
}

inline phi::DataLayout StringToDataLayout(const std::string& str) {
  std::string s(str);
  for (size_t i = 0; i < s.size(); ++i) {
    s[i] = toupper(s[i]);
  }

  if (s == "NHWC") {
    return phi::DataLayout::kNHWC;
  } else if (s == "NCHW") {
    return phi::DataLayout::kNCHW;
  } else if (s == "ANYLAYOUT") {
    return phi::DataLayout::kAnyLayout;
  } else if (s == "MKLDNNLAYOUT") {
    return phi::DataLayout::kMKLDNN;
  } else if (s == "SPARSE_COO") {
    return phi::DataLayout::SPARSE_COO;
  } else if (s == "SPARSE_CSR") {
    return phi::DataLayout::SPARSE_CSR;
  } else {
    PADDLE_THROW(
        phi::errors::InvalidArgument("Layout %s is not supported.", s.c_str()));
  }
  return phi::DataLayout::UNDEFINED;
}

inline void ExtractNCDWH(const phi::DDim& dims,
                         const phi::DataLayout& data_layout,
                         int* N,
                         int* C,
                         int* D,
                         int* H,
                         int* W) {
  *N = dims[0];

  if (dims.size() == 3) {  // Shape is 3-dimensional, and the index value
                           // ranges from 0 to 2.
    *C = data_layout == phi::DataLayout::kNCHW ? dims[1] : dims[2];
    *D = 1;
    *H = 1;
    *W = data_layout == phi::DataLayout::kNCHW ? dims[2] : dims[1];
  } else if (dims.size() == 4) {  // Shape is 4-dimensional, and the index value
                                  // ranges from 0 to 3.
    *C = data_layout == phi::DataLayout::kNCHW ? dims[1] : dims[3];
    *D = 1;
    *H = data_layout == phi::DataLayout::kNCHW ? dims[2] : dims[1];
    *W = data_layout == phi::DataLayout::kNCHW ? dims[3] : dims[2];
  } else {
    *C = data_layout == phi::DataLayout::kNCHW ? dims[1] : dims[4];
    *D = data_layout == phi::DataLayout::kNCHW ? dims[2] : dims[1];
    *H = data_layout == phi::DataLayout::kNCHW ? dims[3] : dims[2];
    *W = data_layout == phi::DataLayout::kNCHW ? dims[4] : dims[3];
  }
}

template <typename T>
inline std::vector<T> get_new_data_from_tensor(
    const phi::CustomContext& dev_ctx,
    const phi::DenseTensor* new_data_tensor) {
  std::vector<T> vec_new_data;
  auto* new_data = new_data_tensor->data<T>();
  phi::DenseTensor cpu_starts_tensor;
  if (new_data_tensor->place().GetType() == phi::AllocationType::CUSTOM) {
    TensorCopy(
        dev_ctx, *new_data_tensor, true, &cpu_starts_tensor, phi::CPUPlace());
    new_data = cpu_starts_tensor.data<T>();
  }
  vec_new_data = std::vector<T>(new_data, new_data + new_data_tensor->numel());
  return vec_new_data;
}

template <typename T>
inline void FillGcuTensorWithConstant(phi::DenseTensor* dst,
                                      const phi::CustomContext& dev_ctx,
                                      T val) {
  int numel = dst->numel();
  std::vector<T, PinnedAllocatorForSTL<T>> src(numel, static_cast<T>(val));
  TensorFromVector(dev_ctx, src, dev_ctx, dst);
  //   dev_ctx.Wait();
}

template <>
inline void FillGcuTensorWithConstant<bool>(phi::DenseTensor* dst,
                                            const phi::CustomContext& dev_ctx,
                                            bool val) {
  int numel = dst->numel();
  std::vector<bool> src(numel, val);
  TensorFromVector<bool>(dev_ctx, src, dev_ctx, dst);
  //   dev_ctx.Wait();
}

}  // namespace custom_kernel
