from os.path import expanduser

from keras import Input, Model
from keras.layers import TimeDistributed, Flatten
from self_supervised_3d_tasks.data.data_generator import get_data_generators

from self_supervised_3d_tasks.algorithms import patch_utils
from self_supervised_3d_tasks.custom_preprocessing.jigsaw_preprocess import preprocess
from self_supervised_3d_tasks.keras_models.fully_connected import fully_connected

from self_supervised_3d_tasks.keras_models.res_net_2d import get_res_net_2d
from self_supervised_3d_tasks.models.cnn_baseline import KaggleGenerator

h_w = 256
split_per_side = 3
dim = (h_w, h_w)
patch_jitter = 10
patch_dim = int((h_w / split_per_side) - patch_jitter)
n_channels = 3
lr = 1e-3
embed_dim = 1000
architecture = "ResNet50"
# data_dir="/mnt/mpws2019cl1/retinal_fundus/left/max_256/"
data_dir = "/mnt/mpws2019cl1/kaggle_retina/train/resized"
train_test_split = 0.9
model_checkpoint = \
    expanduser('~/workspace/self-supervised-transfer-learning/jigsaw_ukb_retina/weights-improvement-01.hdf5')


def apply_model():
    perms, _ = patch_utils.load_permutations()
    input_x = Input((split_per_side * split_per_side, patch_dim, patch_dim, n_channels))

    enc_model = get_res_net_2d(input_shape=[patch_dim, patch_dim, n_channels], classes=embed_dim,
                               architecture=architecture,
                               learning_rate=lr)

    x = TimeDistributed(enc_model)(input_x)
    x = Flatten()(x)
    out = fully_connected(x, num_classes=len(perms))

    model = Model(inputs=input_x, outputs=out)
    model.compile(optimizer='adam',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    model.summary()

    return enc_model, model


def get_training_model():
    return apply_model()[1]


def get_training_generators(batch_size, dataset_name):
    perms, _ = patch_utils.load_permutations()

    def f_train(x, y):  # not using y here, as it gets generated
        return preprocess(x, split_per_side, patch_jitter, perms, is_training=True)

    def f_val(x, y):
        return preprocess(x, split_per_side, patch_jitter, perms, is_training=False)

    # TODO: switch dataset
    train_data, validation_data = get_data_generators(data_dir, train_split=train_test_split,
                                                      train_data_generator_args={"batch_size": batch_size,
                                                                                 "dim": dim,
                                                                                 "n_channels": n_channels,
                                                                                 "pre_proc_func": f_train},
                                                      test_data_generator_args={"batch_size": batch_size,
                                                                                "dim": dim,
                                                                                "n_channels": n_channels,
                                                                                "pre_proc_func": f_val})
    return train_data, validation_data


def get_finetuning_generators(batch_size, dataset_name, training_proportion):
    perms = [range(split_per_side*split_per_side)]

    def f_train(x, y):
        return preprocess(x, split_per_side, patch_jitter, perms, is_training=True)[0], y

    def f_val(x, y):
        return preprocess(x, split_per_side, patch_jitter, perms, is_training=False)[0], y

    # TODO: move this switch to get_data_generators
    if dataset_name == "kaggle_retina":
        gen = KaggleGenerator(batch_size=batch_size, split=training_proportion, shuffle=False,
                              pre_proc_func_train=f_train, pre_proc_func_val=f_val)
        gen_test = KaggleGenerator(batch_size=batch_size, split=train_test_split, shuffle=False,
                                   pre_proc_func_train=f_train, pre_proc_func_val=f_val)
        x_test, y_test = gen_test.get_val_data()

        return gen, x_test, y_test
    else:
        raise ValueError("not implemented")


def get_finetuning_model(load_weights, freeze_weights, num_classes=5):
    enc_model, model_full = apply_model()

    if load_weights:
        model_full.load_weights(model_checkpoint)

    if freeze_weights:
        # freeze the encoder weights
        enc_model.trainable = False

    layer_in = Input((split_per_side * split_per_side, patch_dim, patch_dim, n_channels))
    layer_out = TimeDistributed(enc_model)(layer_in)

    x = Flatten()(layer_out)
    out = fully_connected(x, num_classes=num_classes)

    model = Model(inputs=layer_in, outputs=out)
    model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])

    return model
