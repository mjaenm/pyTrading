import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone


class TimeSeriesEstimator(BaseEstimator):

    #TODO add set params method
    def __init__(self, base_estimator, n_prev=3, n_ahead=1, parallel_models=False, **base_params):
        self.base_estimator = base_estimator.set_params(**base_params)
        self.parallel_models = parallel_models
        self.n_prev = n_prev
        self.n_ahead = n_ahead

        self._fit_estimators = None

    def set_params(self, **params):
        for param, value in params.iteritems():
            if param in self.get_params():
                super(TimeSeriesEstimator, self).set_params(**{param: value})
            else:
                self.base_estimator.set_params(**{param: value})
        return self

    def __repr__(self):
        return "TimeSeriesEstimator: " + repr(self.base_algorithm)

    def _window_dataset(self, n_prev, dataX, dataY=None, n_ahead=1):
        """
        converts a dataset into an autocorrelation dataset with number of previous time steps = n_prev
        returns a an X dataset of shape (samples,timesteps,features) and a Y dataset of shape (samples,features)
        """
        is_pandas = isinstance(dataX, pd.DataFrame)

        if dataY is not None:
            #assert (type(dataX) is type(dataY)) TODO find way to still perform this check
            assert (len(dataX) == len(dataY))

        dlistX, dlistY = [], []
        for i in range(len(dataX) - n_prev + 1 - n_ahead):
            if is_pandas:
                dlistX.append(dataX.iloc[i:i + n_prev].as_matrix())
                if dataY is not None:
                    dlistY.append(dataY.iloc[i + n_prev - 1 + n_ahead].as_matrix())
                else:
                    dlistY.append(dataX.iloc[i + n_prev - 1 + n_ahead].as_matrix())
            else:
                dlistX.append(dataX[i:i + n_prev])
                if dataY is not None:
                    dlistY.append(dataY[i + n_prev - 1 + n_ahead])
                else:
                    dlistY.append(dataX[i + n_prev - 1 + n_ahead])

        darrX = np.array(dlistX)
        darrY = np.array(dlistY)
        return darrX, darrY

    def _unravel_window_data(self, data):
        dlist = []
        one_dim = True if len(data.shape) == 2 else False
        for i in range(data.shape[0]):
            if one_dim:
                dlist.append(data[i, :].ravel())
            else:
                dlist.append(data[i, :, :].ravel())
        return np.array(dlist)

    def offset_data(self,Y):
        if len(Y.shape) > 1:
            return Y[self.n_prev - 1 + self.n_ahead:, :]
        else:
            return Y[self.n_prev - 1 + self.n_ahead:]

    def _preprocess(self, X, Y):
        X_wind, Y_data = self._window_dataset(self.n_prev, X, Y, self.n_ahead)
        X_data = self._unravel_window_data(X_wind)
        return X_data, Y_data

    def fit(self, X, Y=None):
        ''' X and Y are datasets in chronological order, or X is a time series '''
        X_data, Y_data = self._preprocess(X, Y)

        if self.parallel_models and len(Y_data.shape) > 1 and Y_data.shape[1] > 1:
            self._fit_estimators = [clone(self.base_estimator) for i in range(Y_data.shape[1])]
            for i, estimator in enumerate(self._fit_estimators):
                estimator.fit(X_data, Y_data[:, i])
        else:
            self.base_estimator.fit(X_data, Y_data)

        return self


class TimeSeriesRegressor(TimeSeriesEstimator, RegressorMixin):
    def score(self, X, Y, **kwargs):
        return self.base_estimator.score(*self._preprocess(X, Y), **kwargs)

    def predict(self, X):
        X_new = self._preprocess(X, Y=None)[0]

        if self._fit_estimators is not None:
            results = []
            for estimator in self._fit_estimators:
                results.append(estimator.predict(X_new))
            return np.transpose(np.array(results))
        else:
            return self.base_estimator.predict(X_new)


def time_series_split(X, test_size=.2, output_numpy=True):
    is_pandas = isinstance(X, pd.DataFrame) or isinstance(X, pd.Series)
    ntrn = int(len(X) * (1 - test_size))

    if is_pandas:
        X_train = X.iloc[0:ntrn]
        X_test = X.iloc[ntrn:]
    else:
        X_train = X[0:ntrn]
        X_test = X[ntrn:]

    if output_numpy and is_pandas:
        return X_train.as_matrix(), X_test.as_matrix()
    else:
        return X_train, X_test
