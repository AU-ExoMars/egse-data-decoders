"""A base class to simplify model fitting."""

import inspect
import typing

import numpy as np
import scipy


class FittableModel:
    """A base class to simplify model fitting.

    I'm finding myself writing a variety of things along the lines of "this
    is the theoretical formula, with a bunch of parameters. Use some data
    and scipy.optimize.curve_fit to come up with the parameters.

    The problem is that curve_fit uses introspection to determine the number
    of parameters it's optimising, and that means you end up with a bunch of
    very similar functions.

    This base class uses Python's "inspect" module to change the signature
    of a base function so that curve_fit can use it.

    Subclasses need to provide an __init__ method which calls this class
    with the list of parameters, and a __call__ method which returns the
    result of doing a calculation. The base class provides a "calibrate"
    method which performs the curve_fit using the constructor-provided
    parameters and the __call__ method.

    Example:
    class LinearModel(FittableModel):
        def __init__(self, a: float|None = None, b: float|None = None):
            super().__init__(a=a, b=b)

        def __call__(self, x: float|np.ndarray):
            return self.a*x + self.b

    l = LinearModel()
    rmse = l.calibrate([1,2,3,4,5], [2,4,6,8,10])
    print(f"RMS error = {rmse:.5g}")
    print(l)

    """

    def __init__(self, **kwargs: float|tuple[float, float]) -> None:
        """Configure model calibration using the supplied kwargs.

        This saves kwargs entries as model attributes, keeps a list of
        their names and makes a function whose signature tells
        scipy.optimize.curve_fit what to do.

        Subclasses should pass model parameters upwards to here, by name.
        """
        # We'll store them as attributes and define a function whose
        # signature appears to use them.
        #
        # If the supplied value is a tuple, then it will be treated as
        # bounds for calibration, rather than an actual value.

        self.__bounds = [[], []]

        for name, value in kwargs.items():
            if isinstance(value, tuple) and len(value) == 2:
                self.__bounds[0].append(value[0])
                self.__bounds[1].append(value[1])
                value = None
            else:
                self.__bounds[0].append(-np.inf)
                self.__bounds[1].append(np.inf)
            setattr(self, name, value)

        # Store the list of parameter names.
        self.__model_params = list(kwargs.keys())

        def calibration_estimator(x_values: np.ndarray, *args: list[float]) -> float:
            """Evaluate the model, given supplied parameters.

            This function will become __calibration_estimator and is the
            function that scipy.optimize.curve_fit will call. We take the
            passed arguments, store them into our model parameters and then
            call our own __call__ to generate the prediction that curve_fit
            will optimise.
            """
            for i, name in enumerate(self.__model_params):
                setattr(self, name, float(args[i]))
            return self.__call__(x_values)

        # But curve_fit uses introspection to decide how to
        # call the estimator. So we need to make calibration_estimator
        # look like it takes our model parameters as its own parameters.
        # This magic does that. It gets hold of the function's signature,
        # strips off the "args" parameter and adds parameters for each
        # of the model parameters that were supplied via the constructor.

        # Get hold of the signature.
        sig = inspect.signature(calibration_estimator)

        # New array for the parameter entries.
        parameters = [ param
            for param in sig.parameters.values()
                if param.name != "args"
        ]

        # Add in the "fake" parameters for curve_fit.
        parameters += [
            inspect.Parameter(
                name = name,
                kind = inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            for name in self.__model_params
        ]

        # Replace our function's signature and store it into the object as
        # __calibration_estimator.
        calibration_estimator.__signature__ = sig.replace(parameters=parameters)

        self.__calibration_estimator = calibration_estimator

    def calibrate(self,
            x_values: list|np.ndarray,
            y_values: list|np.ndarray,
            calibration_estimator: typing.Callable[float|np.ndarray, float]|None = None,
            **kwargs: typing.Any,
        ) -> float:
        """Optimise model parameters, given some x and y data."""
        x_values = np.array(x_values)
        y_values = np.array(y_values)

        if calibration_estimator is None:
            calibration_estimator = self.__calibration_estimator

        if "bounds" not in kwargs:
            kwargs["bounds"] = self.__bounds
        model, _covar = scipy.optimize.curve_fit(
            calibration_estimator,
            x_values, y_values,
            **kwargs,
        )

        predicted = calibration_estimator(x_values, *model)

        return np.sqrt(sum((y_values - predicted)**2)/y_values.shape[0])

    def __str__(self) -> str:
        """Return a representation of the object."""
        params = ", ".join([
            f"{name}={getattr(self, name)}"
                for name in self.__model_params
        ])
        return f"{self.__class__.__name__}({params})"

if __name__ == "__main__":
    class LinearModel(FittableModel):
        """An example of how to use FittableModel.

        This is a simple linear model. Its constructor takes slope
        and intercept parameters and passes them up to FittableModel.
        Its __call__ method does the calculation.

        Actual fitting, if needed, is done by FittableModels's
        calibrate() method.
        """

        def __init__(self,
            slope: float|None = None,
            intercept: float|None = None,
        ) -> None:
            """Call the parent constructor to store the parameters."""
            super().__init__(slope=slope, intercept=intercept)

        def __call__(self, x: float|np.ndarray) -> float:
            """Perform the model calculation."""
            return self.slope*x + self.intercept

    lm = LinearModel()
    rmse = lm.calibrate([1,2,3,4,5], [2,4,6,8,10])
    print(f"RMS error = {rmse:.5g}")
    print(lm)

