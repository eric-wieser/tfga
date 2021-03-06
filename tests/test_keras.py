from tfga.layers import (
    GeometricProductDense, GeometricSandwichProductDense,
    GeometricToTensor, GeometricToTensorWithKind,
    TensorToGeometric, TensorWithKindToGeometric
)
from tfga.blades import BladeKind
from tfga import GeometricAlgebra
from tensorflow import keras as ks
import unittest as ut
import tensorflow as tf

# Make tensorflow not take over the entire GPU memory
for gpu in tf.config.experimental.list_physical_devices('GPU'):
    tf.config.experimental.set_memory_growth(gpu, True)


class TestKerasLayers(ut.TestCase):
    def assertTensorsEqual(self, a, b):
        self.assertTrue(tf.reduce_all(a == b), "%s not equal to %s" % (a, b))

    def test_tensor_to_geometric(self):
        sta = GeometricAlgebra([1, -1, -1, -1])
        tensor = tf.ones([32, 4])
        gt_geom_tensor = tf.concat(
            [tf.zeros([32, 1]), tf.ones([32, 4]), tf.zeros([32, 11])],
            axis=-1
        )

        vector_blade_indices = [1, 2, 3, 4]

        tensor_to_geom_layer = TensorToGeometric(sta, vector_blade_indices)

        self.assertTensorsEqual(tensor_to_geom_layer(tensor), gt_geom_tensor)

    def test_tensor_with_kind_to_geometric(self):
        sta = GeometricAlgebra([1, -1, -1, -1])
        tensor = tf.ones([32, 4])
        gt_geom_tensor = tf.concat(
            [tf.zeros([32, 1]), tf.ones([32, 4]), tf.zeros([32, 11])],
            axis=-1
        )

        vector_blade_indices = [1, 2, 3, 4]

        tensor_kind_to_geom_layer = TensorWithKindToGeometric(
            sta, BladeKind.VECTOR)

        self.assertTensorsEqual(
            tensor_kind_to_geom_layer(tensor), gt_geom_tensor)

    def test_geometric_to_tensor(self):
        sta = GeometricAlgebra([1, -1, -1, -1])
        gt_tensor = tf.ones([32, 4])
        geom_tensor = tf.concat(
            [tf.zeros([32, 1]), tf.ones([32, 4]), tf.zeros([32, 11])],
            axis=-1
        )

        vector_blade_indices = [1, 2, 3, 4]

        geom_to_tensor_layer = GeometricToTensor(sta, vector_blade_indices)

        self.assertTensorsEqual(geom_to_tensor_layer(geom_tensor), gt_tensor)

    def test_geometric_to_tensor_with_kind(self):
        sta = GeometricAlgebra([1, -1, -1, -1])
        gt_tensor = tf.ones([32, 4])
        geom_tensor = tf.concat(
            [tf.zeros([32, 1]), tf.ones([32, 4]), tf.zeros([32, 11])],
            axis=-1
        )

        vector_blade_indices = [1, 2, 3, 4]

        geom_to_tensor_kind_layer = GeometricToTensorWithKind(
            sta, BladeKind.VECTOR)

        self.assertTensorsEqual(
            geom_to_tensor_kind_layer(geom_tensor), gt_tensor)

    def test_geometric_product_dense_v_v(self):
        sta = GeometricAlgebra([1, -1, -1, -1])

        geom_tensor = tf.concat(
            [tf.zeros([32, 6, 1]), tf.ones([32, 6, 4]), tf.zeros([32, 6, 11])],
            axis=-1
        )

        vector_blade_indices = [1, 2, 3, 4]

        geom_prod_layer = GeometricProductDense(
            sta, 8,
            blade_indices_kernel=vector_blade_indices,
            blade_indices_bias=vector_blade_indices,
            bias_initializer=tf.keras.initializers.RandomNormal()
        )

        result = geom_prod_layer(geom_tensor)

        # vector * vector + vector -> scalar + bivector + vector
        expected_result_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        self.assertTrue(sta.is_pure(result, expected_result_indices))

    def test_geometric_product_dense_s_mv(self):
        sta = GeometricAlgebra([1, -1, -1, -1])

        geom_tensor = tf.concat(
            [tf.ones([20, 6, 1]), tf.zeros([20, 6, 15])],
            axis=-1
        )

        mv_blade_indices = list(range(16))

        geom_prod_layer = GeometricProductDense(
            sta, 8,
            blade_indices_kernel=mv_blade_indices,
            blade_indices_bias=mv_blade_indices
        )

        result = geom_prod_layer(geom_tensor)

        # scalar * multivector + multivector -> multivector
        # Check that nothing is zero (it would be extremely unlikely
        # but not impossible to randomly get a zero here).
        self.assertTrue(tf.reduce_all(result != 0.0))

    def test_geometric_product_dense_sequence(self):
        sta = GeometricAlgebra([1, -1, -1, -1])

        tensor = tf.ones([20, 6, 4])

        vector_blade_indices = [1, 2, 3, 4]
        mv_blade_indices = list(range(16))

        # vector * vector + vector -> scalar + bivector + vector
        scalar_bivector_blade_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        sequence = tf.keras.Sequential([
            TensorToGeometric(sta, blade_indices=vector_blade_indices),
            GeometricProductDense(
                sta, 8,
                blade_indices_kernel=vector_blade_indices,
                blade_indices_bias=vector_blade_indices,
                bias_initializer=tf.keras.initializers.RandomNormal()
            ),
            GeometricToTensor(sta, blade_indices=scalar_bivector_blade_indices)
        ])

        result = sequence(tensor)

        self.assertEqual(result.shape[-1], len(scalar_bivector_blade_indices))

    def test_geometric_sandwich_product_dense_v_v(self):
        sta = GeometricAlgebra([1, -1, -1, -1])

        geom_tensor = tf.concat(
            [tf.zeros([32, 6, 1]), tf.ones([32, 6, 4]), tf.zeros([32, 6, 11])],
            axis=-1
        )

        vector_blade_indices = [1, 2, 3, 4]

        result_indices = tf.concat([
            sta.get_kind_blade_indices(BladeKind.VECTOR),
            sta.get_kind_blade_indices(BladeKind.TRIVECTOR)
        ], axis=0)

        geom_prod_layer = GeometricSandwichProductDense(
            sta, 8,
            blade_indices_kernel=vector_blade_indices,
            blade_indices_bias=result_indices,
            bias_initializer=tf.keras.initializers.RandomNormal()
        )

        result = geom_prod_layer(geom_tensor)

        # vector * vector * ~vector + vector -> vector + trivector

        self.assertTrue(sta.is_pure(result, result_indices))
