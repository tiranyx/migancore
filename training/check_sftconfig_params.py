from trl import SFTConfig
import inspect
sig = inspect.signature(SFTConfig.__init__)
for name, param in sig.parameters.items():
    if name != 'self':
        print(name, '=', param.default)
