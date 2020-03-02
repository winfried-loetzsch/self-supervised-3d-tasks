from self_supervised_3d_tasks.keras_algorithms.custom_utils import init
from self_supervised_3d_tasks.keras_algorithms.keras_train_algo import keras_algorithm_list
from self_supervised_3d_tasks.keras_algorithms import keras_test_algo as ts
import numpy as np


def trial(algorithm, dataset_name, loss, metrics, epochs=5, batch_size=8, lr=1e-3, scores=("qw_kappa_kaggle",),
          model_checkpoint=None, load_weights=False, epochs_warmup=0, **kwargs):
    algorithm_def = keras_algorithm_list[algorithm].create_instance(**kwargs)
    f_train, f_val = algorithm_def.get_finetuning_preprocessing()
    x_test, y_test = ts.get_dataset_test(dataset_name, batch_size, f_val, kwargs)

    def get_data_norm_npy(path):
        img = np.load(path)
        img = (img - img.min()) / (img.max() - img.min())

        return img

    # test function for making a sample prediction that can be visualized
    def model_callback(model):
        p1 = "/mnt/mpws2019cl1/Task07_Pancreas/images_resized_128_labeled/train/pancreas_052.npy"
        data = get_data_norm_npy(p1)

        data = np.expand_dims(data, axis=0)
        result = model.predict(data, batch_size=batch_size)

        print(data.shape)
        print(result.shape)

        np.save("prediction.npy", result)

    ts.run_single_test(
        algorithm_def=algorithm_def,
        dataset_name=dataset_name,
        train_split=1,
        load_weights=load_weights,
        freeze_weights=False,
        x_test=x_test,
        y_test=y_test,
        lr=lr,
        batch_size=batch_size,
        epochs=epochs,
        epochs_warmup=epochs_warmup,
        model_checkpoint=model_checkpoint,
        scores=scores,
        loss=loss,
        metrics=metrics,
        logging_path=None,
        kwargs=kwargs,
        model_callback=model_callback
    )


if __name__ == "__main__":
    init(trial)
