#  Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import numpy as np
import unittest
import copy

from paddle.base import Program, program_guard
import paddle.base as base
import paddle
from op_test import OpTest, skip_check_grad_ci

paddle.enable_static()


class TestElementwiseAddOp(OpTest):
    def check_grad_with_place(
        self,
        place,
        inputs_to_check,
        output_names,
        no_grad_set=None,
        numeric_grad_delta=0.005,
        in_place=False,
        max_relative_error=0.005,
        user_defined_grads=None,
        user_defined_grad_outputs=None,
        check_dygraph=True,
        numeric_place=None,
    ):
        if user_defined_grads is None:
            dx = np.divide(np.ones_like(self.x, dtype=self.dtype), self.x.size)
            dy = np.divide(np.ones_like(self.y, dtype=self.dtype), self.y.size)
            if no_grad_set is None:
                user_defined_grads = [dx, dy]
            elif "X" in no_grad_set and "Y" in no_grad_set:
                user_defined_grads = None
            elif "X" in no_grad_set:
                user_defined_grads = [dy]
            elif "Y" in no_grad_set:
                user_defined_grads = [dx]

        super().check_grad_with_place(
            place,
            inputs_to_check,
            output_names,
            no_grad_set,
            numeric_grad_delta,
            in_place,
            max_relative_error,
            user_defined_grads,
            user_defined_grad_outputs,
            check_dygraph,
            numeric_place,
        )

    def setUp(self):
        self.set_sdaa()
        self.op_type = "elementwise_add"
        self.python_api = paddle.add
        self.init_dtype()
        self.init_input_output()
        self.init_kernel_type()
        self.init_axis()

        self.inputs = {
            "X": OpTest.np_dtype_to_base_dtype(self.x),
            "Y": OpTest.np_dtype_to_base_dtype(self.y),
        }
        self.attrs = {"axis": self.axis, "use_mkldnn": self.use_mkldnn}
        self.outputs = {"Out": self.out}

    def set_sdaa(self):
        self.__class__.use_custom_device = True
        self.place = paddle.CustomPlace("sdaa", 0)

    def init_kernel_type(self):
        self.use_mkldnn = False

    def init_input_output(self):
        self.x = np.random.uniform(0.1, 1, [14, 17]).astype(self.dtype)
        self.y = np.random.uniform(0.1, 1, [14, 17]).astype(self.dtype)
        self.out = np.add(self.x, self.y)

    def init_dtype(self):
        self.dtype = np.float32

    def init_axis(self):
        self.axis = -1

    def test_check_output(self):
        self.check_output_with_place(self.place)

    def test_check_grad_normal(self):
        if (
            self.dtype == np.uint8
            or self.dtype == np.int8
            or self.dtype == np.int16
            or self.dtype == np.int32
            or self.dtype == np.int64
        ):
            return
        self.check_grad_with_place(
            self.place,
            ["X", "Y"],
            "Out",
        )

    def test_check_grad_ingore_x(self):
        if (
            self.dtype == np.uint8
            or self.dtype == np.int8
            or self.dtype == np.int16
            or self.dtype == np.int32
            or self.dtype == np.int64
        ):
            return

        self.check_grad_with_place(
            self.place,
            ["Y"],
            "Out",
            no_grad_set=set("X"),
        )

    def test_check_grad_ingore_y(self):
        if (
            self.dtype == np.uint8
            or self.dtype == np.int8
            or self.dtype == np.int16
            or self.dtype == np.int32
            or self.dtype == np.int64
        ):
            return

        self.check_grad_with_place(
            self.place,
            ["X"],
            "Out",
            no_grad_set=set("Y"),
        )


class TestFP16ElementwiseAddOp(TestElementwiseAddOp):
    def init_dtype(self):
        self.dtype = np.float16


class TestDoubleElementwiseAddOp(TestElementwiseAddOp):
    def init_dtype(self):
        self.dtype = np.double


class TestUint8ElementwiseAddOp(TestElementwiseAddOp):
    def init_dtype(self):
        self.dtype = np.uint8

    def init_input_output(self):
        self.x = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.y = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.out = np.add(self.x, self.y)


class TestInt8ElementwiseAddOp(TestElementwiseAddOp):
    def init_dtype(self):
        self.dtype = np.int8

    def init_input_output(self):
        self.x = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.y = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.out = np.add(self.x, self.y)


class TestInt16ElementwiseAddOp(TestElementwiseAddOp):
    def init_dtype(self):
        self.dtype = np.int16

    def init_input_output(self):
        self.x = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.y = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.out = np.add(self.x, self.y)


class TestInt32ElementwiseAddOp(TestElementwiseAddOp):
    def init_dtype(self):
        self.dtype = np.int32

    def init_input_output(self):
        self.x = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.y = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.out = np.add(self.x, self.y)


class TestElementwiseGradAddOp(OpTest):
    def check_grad_with_place(
        self,
        place,
        inputs_to_check,
        output_names,
        no_grad_set=None,
        numeric_grad_delta=0.005,
        in_place=False,
        max_relative_error=0.005,
        user_defined_grads=None,
        user_defined_grad_outputs=None,
        check_dygraph=True,
        numeric_place=None,
    ):
        if user_defined_grads is None:
            dx = np.divide(np.ones_like(self.x, dtype=self.dtype), self.x.size)
            dy = np.divide(np.ones_like(self.y, dtype=self.dtype), self.y.size)
            if no_grad_set is None:
                user_defined_grads = [dx, dy]
            elif "X" in no_grad_set and "Y" in no_grad_set:
                user_defined_grads = None
            elif "X" in no_grad_set:
                user_defined_grads = [dy]
            elif "Y" in no_grad_set:
                user_defined_grads = [dx]

        super().check_grad_with_place(
            place,
            inputs_to_check,
            output_names,
            no_grad_set,
            numeric_grad_delta,
            in_place,
            max_relative_error,
            user_defined_grads,
            user_defined_grad_outputs,
            check_dygraph,
            numeric_place,
        )

    def setUp(self):
        self.set_sdaa()
        self.op_type = "grad_add"
        self.init_dtype()
        self.init_input_output()
        self.init_kernel_type()
        self.init_axis()

        self.inputs = {
            "X": OpTest.np_dtype_to_base_dtype(self.x),
            "Y": OpTest.np_dtype_to_base_dtype(self.y),
        }
        self.attrs = {"axis": self.axis, "use_mkldnn": self.use_mkldnn}
        self.outputs = {"Out": self.out}

    def set_sdaa(self):
        self.__class__.use_custom_device = True
        self.place = paddle.CustomPlace("sdaa", 0)

    def init_kernel_type(self):
        self.use_mkldnn = False

    def init_input_output(self):
        self.x = np.random.uniform(0.1, 1, [14, 17]).astype(self.dtype)
        self.y = np.random.uniform(0.1, 1, [14, 17]).astype(self.dtype)
        self.out = np.add(self.x, self.y)

    def init_dtype(self):
        self.dtype = np.float32

    def init_axis(self):
        self.axis = -1

    def test_check_output(self):
        self.check_output_with_place(self.place)


class TestINT64ElementwiseAddOp(TestElementwiseAddOp):
    def init_dtype(self):
        self.dtype = np.int64

    def init_input_output(self):
        self.x = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.y = np.random.randint(2, 10, [14, 17]).astype(self.dtype)
        self.out = np.add(self.x, self.y)


class TestElementwiseAddOpNd1(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.uniform(0.1, 1, [4, 7, 5, 4, 6]).astype(self.dtype)
        self.y = np.random.uniform(0.1, 1, [4, 7, 5, 4, 6]).astype(self.dtype)
        self.out = np.add(self.x, self.y)

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestElementwiseAddOpNd2(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.uniform(0.1, 1, [4, 7, 5, 4, 3, 6]).astype(self.dtype)
        self.y = np.random.uniform(0.1, 1, [4, 7, 5, 4, 3, 6]).astype(self.dtype)
        self.out = np.add(self.x, self.y)

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


@skip_check_grad_ci(reason="[skip shape check] Use y_shape(1) to test broadcast.")
class TestElementwiseAddOp_scalar(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 4).astype(self.dtype)
        self.y = np.random.rand(1).astype(self.dtype)
        self.out = self.x + self.y


@skip_check_grad_ci(reason="[skip shape check] Use y_shape(1) to test broadcast.")
class TestFP16ElementwiseAddOp_scalar(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 4).astype(self.dtype)
        self.y = np.random.rand(1).astype(self.dtype)
        self.out = self.x + self.y


@skip_check_grad_ci(reason="[skip shape check] Use y_shape(1,1) to test broadcast.")
class TestElementwiseAddOp_scalar2(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 4).astype(self.dtype)
        self.y = np.random.rand(1, 1).astype(self.dtype)
        self.out = self.x + self.y


@skip_check_grad_ci(reason="[skip shape check] Use y_shape(1,1) to test broadcast.")
class TestFP16ElementwiseAddOp_scalar2(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 4).astype(self.dtype)
        self.y = np.random.rand(1, 1).astype(self.dtype)
        self.out = self.x + self.y


class TestAddAPI(unittest.TestCase):
    def test_name(self):
        with paddle.static.program_guard(paddle.static.Program()):
            x = paddle.static.data(name="x", shape=[2, 3], dtype="float32")
            y = paddle.static.data(name="y", shape=[2, 3], dtype="float32")

            y_1 = paddle.add(x, y, name="add_res")
            self.assertEqual(("add_res" in y_1.name), True)

    def test_static(self):
        with paddle.static.program_guard(paddle.static.Program()):

            x_np = np.array([2, 3, 4]).astype("float32")
            y_np = np.array([1, 5, 2]).astype("float32")

            x = paddle.static.data(name="x", shape=[3], dtype="float32")
            y = paddle.static.data(name="y", shape=[3], dtype="float32")

            x_reshape = paddle.reshape(x, [3, 1])
            y_reshape = paddle.reshape(y, [3, 1])
            z = paddle.add(x_reshape, y_reshape)
            z = paddle.reshape(z, shape=[3])

            place = paddle.CustomPlace("sdaa", 0)
            exe = paddle.static.Executor(place)
            x_value, y_value, z_value = exe.run(
                feed={"x": x_np, "y": y_np}, fetch_list=[x, y, z]
            )

            z_expected = np.array([3.0, 8.0, 6.0])
            self.assertEqual(
                (x_value == x_np).all(),
                True,
                msg="x_value = {}, but expected {}".format(x_value, x_np),
            )
            self.assertEqual(
                (y_value == y_np).all(),
                True,
                msg="y_value = {}, but expected {}".format(y_value, y_np),
            )
            self.assertEqual(
                (z_value == z_expected).all(),
                True,
                msg="z_value = {}, but expected {}".format(z_value, z_expected),
            )


class TestAddError(unittest.TestCase):
    def test_errors(self):
        with paddle.static.program_guard(paddle.static.Program()):
            # the input of elementwise_add must be Variable.
            x1 = base.create_lod_tensor(
                np.array([-1, 3, 5, 5]), [[1, 1, 1, 1]], paddle.CustomPlace("sdaa", 0)
            )
            y1 = base.create_lod_tensor(
                np.array([-1, 3, 5, 5]), [[1, 1, 1, 1]], paddle.CustomPlace("sdaa", 0)
            )
            self.assertRaises(TypeError, paddle.add, x1, y1)

            # the input dtype must be float16 or float32 or float64 or int32 or int64
            x2 = paddle.static.data(name="x2", shape=[3, 4, 5, 6], dtype="uint8")
            y2 = paddle.static.data(name="y2", shape=[3, 4, 5, 6], dtype="uint8")
            self.assertRaises(TypeError, paddle.add, x2, y2)


class TestElementwiseAddOp_Vector(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.random((100,)).astype(self.dtype)
        self.y = np.random.random((100,)).astype(self.dtype)
        self.out = np.add(self.x, self.y)

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_Vector(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.random((100,)).astype(self.dtype)
        self.y = np.random.random((100,)).astype(self.dtype)
        self.out = np.add(self.x, self.y)


class TestElementwiseAddOp_broadcast_0(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 2, 3).astype(self.dtype)
        self.y = np.random.rand(100).astype(self.dtype)
        self.out = self.x + self.y.reshape(100, 1, 1)

    def init_axis(self):
        self.axis = 0

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_broadcast_0(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 2, 3).astype(self.dtype)
        self.y = np.random.rand(100).astype(self.dtype)
        self.out = self.x + self.y.reshape(100, 1, 1)

    def init_axis(self):
        self.axis = 0


class TestElementwiseAddOp_broadcast_1(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 100, 3).astype(self.dtype)
        self.y = np.random.rand(100).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 100, 1)

    def init_axis(self):
        self.axis = 1

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_broadcast_1(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 100, 3).astype(self.dtype)
        self.y = np.random.rand(100).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 100, 1)

    def init_axis(self):
        self.axis = 1


class TestElementwiseAddOp_broadcast_2(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 100).astype(self.dtype)
        self.y = np.random.rand(100).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 1, 100)

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_broadcast_2(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 100).astype(self.dtype)
        self.y = np.random.rand(100).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 1, 100)


class TestElementwiseAddOp_broadcast_3(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 10, 12, 1).astype(self.dtype)
        self.y = np.random.rand(10, 12).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 10, 12, 1)

    def init_axis(self):
        self.axis = 1

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_broadcast_3(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 10, 12, 3).astype(self.dtype)
        self.y = np.random.rand(10, 12).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 10, 12, 1)

    def init_axis(self):
        self.axis = 1


class TestElementwiseAddOp_broadcast_4(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 2, 1, 2).astype(self.dtype)
        self.y = np.random.rand(100, 1).astype(self.dtype)
        self.out = self.x + self.y.reshape(100, 1, 1, 1)

    def init_axis(self):
        self.axis = 0

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_broadcast_4(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 2, 1, 2).astype(self.dtype)
        self.y = np.random.rand(100, 1).astype(self.dtype)
        self.out = self.x + self.y.reshape(100, 1, 1, 1)

    def init_axis(self):
        self.axis = 0


class TestElementwiseAddOp_broadcast_5(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(10, 3, 12).astype(self.dtype)
        self.y = np.random.rand(10, 1, 12).astype(self.dtype)
        self.out = self.x + self.y

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_broadcast_5(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(10, 3, 12).astype(self.dtype)
        self.y = np.random.rand(10, 1, 12).astype(self.dtype)
        self.out = self.x + self.y


class TestElementwiseAddOp_broadcast_6(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 12, 3, 5).astype(self.dtype)
        self.y = np.random.rand(2, 12, 1, 5).astype(self.dtype)
        self.out = self.x + self.y

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestElementwiseAddOp_broadcast_7(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(1, 1, 20, 5).astype(self.dtype)
        self.y = np.random.rand(20, 5, 1, 1).astype(self.dtype)
        self.out = self.x + self.y

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_broadcast_6(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 12, 3, 5).astype(self.dtype)
        self.y = np.random.rand(2, 12, 1, 5).astype(self.dtype)
        self.out = self.x + self.y


class TestElementwiseAddOp_rowwise_add_0(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 10, 12).astype(self.dtype)
        self.y = np.random.rand(10, 12).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 10, 12)

    def init_axis(self):
        self.axis = 1

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_rowwise_add_0(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 10, 12).astype(self.dtype)
        self.y = np.random.rand(10, 12).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 10, 12)

    def init_axis(self):
        self.axis = 1


@skip_check_grad_ci(reason="[skip shape check] Use y_shape(1) to test broadcast.")
class TestElementwiseAddOp_rowwise_add_1(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 1).astype(self.dtype)
        self.y = np.random.rand(1).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 1)

    def init_axis(self):
        self.axis = 1


@skip_check_grad_ci(reason="[skip shape check] Use y_shape(1) to test broadcast.")
class TestFP16ElementwiseAddOp_rowwise_add_1(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 1).astype(self.dtype)
        self.y = np.random.rand(1).astype(self.dtype)
        self.out = self.x + self.y.reshape(1, 1)

    def init_axis(self):
        self.axis = 1


class TestElementwiseAddOp_channelwise_add(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 2, 3).astype(self.dtype)
        self.y = np.random.rand(100, 1, 1).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = -1

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestFP16ElementwiseAddOp_channelwise_add(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(100, 2, 3).astype(self.dtype)
        self.y = np.random.rand(100, 1, 1).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = -1


class TestElementwiseAddOp_commonuse_add1(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 100).astype(self.dtype)
        self.y = np.random.rand(1, 1, 100).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = -1

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestElementwiseFP16AddOp_commonuse_add1(TestFP16ElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(2, 3, 100).astype(self.dtype)
        self.y = np.random.rand(1, 1, 100).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = -1


class TestElementwiseAddOp_commonuse_add2(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(10, 3, 1, 4).astype(self.dtype)
        self.y = np.random.rand(10, 1, 12, 1).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = -1

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestElementwiseAddOp_commonuse_add3(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(10, 3, 1, 4, 2).astype(self.dtype)
        self.y = np.random.rand(10, 1, 12, 4, 2).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = -1

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestElementwiseAddOp_xsize_lessthan_ysize_add(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(10, 12).astype(self.dtype)
        self.y = np.random.rand(2, 2, 10, 12).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = 2

    def test_check_inplace(self):
        self.check_inplace_output_with_place(self.place)


class TestElementwiseAddOp_same_shape_ysize_large(TestElementwiseAddOp):
    def init_input_output(self):
        self.x = np.random.rand(10, 1, 12).astype(self.dtype)
        self.y = np.random.rand(10, 2, 12).astype(self.dtype)
        self.out = self.x + self.y

    def init_axis(self):
        self.axis = 0


class TestElementwiseAddOpError(unittest.TestCase):
    def test_errors(self):
        with program_guard(Program(), Program()):
            # the input of elementwise_add must be Variable.
            x1 = base.create_lod_tensor(
                np.array([-1, 3, 5, 5]), [[1, 1, 1, 1]], paddle.CustomPlace("sdaa", 0)
            )
            y1 = base.create_lod_tensor(
                np.array([-1, 3, 5, 5]), [[1, 1, 1, 1]], paddle.CustomPlace("sdaa", 0)
            )
            self.assertRaises(TypeError, paddle.add, x1, y1)

            # the input dtype of elementwise_add must be float16 or float32 or float64 or int32 or int64
            # float16 only can be set on GPU place
            x2 = paddle.static.data(name="x2", shape=[3, 4, 5, 6], dtype="uint8")
            y2 = paddle.static.data(name="y2", shape=[3, 4, 5, 6], dtype="uint8")
            self.assertRaises(TypeError, paddle.add, x2, y2)


class TestAddApi(unittest.TestCase):
    def _executed_api(self, x, y, name=None):
        return paddle.add(x, y, name)

    def test_name(self):
        with base.program_guard(base.Program()):
            x = paddle.static.data(name="x", shape=[2, 3], dtype="float32")
            y = paddle.static.data(name="y", shape=[2, 3], dtype="float32")

            y_1 = self._executed_api(x, y, name="add_res")
            self.assertEqual(("add_res" in y_1.name), True)

    def test_declarative(self):
        with base.program_guard(base.Program()):

            def gen_data():
                return {
                    "x": np.array([2, 3, 4]).astype("float32"),
                    "y": np.array([1, 5, 2]).astype("float32"),
                }

            x = paddle.static.data(name="x", shape=[3], dtype="float32")
            y = paddle.static.data(name="y", shape=[3], dtype="float32")
            z = self._executed_api(x, y)

            place = paddle.CustomPlace("sdaa", 0)
            exe = base.Executor(place)
            z_value = exe.run(feed=gen_data(), fetch_list=[z.name])
            z_expected = np.array([3.0, 8.0, 6.0])
            self.assertEqual((z_value == z_expected).all(), True)

    def test_dygraph(self):
        with base.dygraph.guard(paddle.CustomPlace("sdaa", 0)):
            np_x = np.array([2, 3, 4]).astype("float32")
            np_y = np.array([1, 5, 2]).astype("float32")
            x = base.dygraph.to_variable(np_x)
            y = base.dygraph.to_variable(np_y)
            z = self._executed_api(x, y)
            np_z = z.numpy()
            z_expected = np.array([3.0, 8.0, 6.0])
            self.assertEqual((np_z == z_expected).all(), True)


class TestAddInplaceApi(TestAddApi):
    def _executed_api(self, x, y, name=None):
        return x.add_(y, name)


class TestAddInplaceBroadcastSuccess(unittest.TestCase):
    def init_data(self):
        self.x_numpy = np.random.rand(2, 3, 4).astype("float")
        self.y_numpy = np.random.rand(3, 4).astype("float")

    def test_broadcast_success(self):
        paddle.disable_static(place=paddle.CustomPlace("sdaa", 0))
        self.init_data()
        x = paddle.to_tensor(self.x_numpy)
        y = paddle.to_tensor(self.y_numpy)
        inplace_result = x.add_(y)
        numpy_result = self.x_numpy + self.y_numpy
        self.assertEqual((inplace_result.numpy() == numpy_result).all(), True)
        paddle.enable_static()


class TestAddInplaceBroadcastSuccess2(TestAddInplaceBroadcastSuccess):
    def init_data(self):
        self.x_numpy = np.random.rand(1, 2, 3, 1).astype("float")
        self.y_numpy = np.random.rand(3, 1).astype("float")


class TestAddInplaceBroadcastSuccess3(TestAddInplaceBroadcastSuccess):
    def init_data(self):
        self.x_numpy = np.random.rand(2, 3, 1, 5).astype("float")
        self.y_numpy = np.random.rand(1, 3, 1, 5).astype("float")


class TestAddInplaceBroadcastError(unittest.TestCase):
    def init_data(self):
        self.x_numpy = np.random.rand(3, 4).astype("float")
        self.y_numpy = np.random.rand(2, 3, 4).astype("float")

    def test_broadcast_errors(self):
        paddle.disable_static(place=paddle.CustomPlace("sdaa", 0))
        self.init_data()
        x = paddle.to_tensor(self.x_numpy)
        y = paddle.to_tensor(self.y_numpy)

        def broadcast_shape_error():
            x.add_(y)

        self.assertRaises(ValueError, broadcast_shape_error)
        paddle.enable_static()


class TestAddInplaceBroadcastError2(TestAddInplaceBroadcastError):
    def init_data(self):
        self.x_numpy = np.random.rand(2, 1, 4).astype("float")
        self.y_numpy = np.random.rand(2, 3, 4).astype("float")


class TestAddInplaceBroadcastError3(TestAddInplaceBroadcastError):
    def init_data(self):
        self.x_numpy = np.random.rand(5, 2, 1, 4).astype("float")
        self.y_numpy = np.random.rand(2, 3, 4).astype("float")


class TestTensorFloa32Bfloat16OrFloat16Add(unittest.TestCase):
    def _floa32_bfloat16_or_float16_add(self, y_dtype):
        paddle.disable_static()

        np.random.seed(2023)

        test_num = 5
        val_range = 10000
        shapes = []
        for i in range(test_num):
            shape = [np.random.randint(1, val_range), np.random.randint(1, val_range)]
            shapes.append(shape)

        for i, shape in enumerate(shapes):
            x = paddle.randn(list(shape), dtype=paddle.float32)
            x_copy = copy.deepcopy(x)
            y = paddle.randn(list(shape), dtype=y_dtype)
            x.add_(y)
            x_copy.add_(paddle.cast(y, paddle.float32))
            np.testing.assert_equal(x.numpy(), x_copy.numpy())
            del x, x_copy


class TestTensorFloa32Bfloat16Add(TestTensorFloa32Bfloat16OrFloat16Add):
    def test_floa32_float16_add(self):
        place = paddle.CustomPlace("sdaa", 0)
        with base.dygraph.base.guard(place=place):
            self._floa32_bfloat16_or_float16_add(y_dtype=paddle.float16)


if __name__ == "__main__":
    unittest.main()
