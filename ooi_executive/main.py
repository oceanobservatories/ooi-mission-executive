#!/usr/bin/env python

from ooi_executive import executive

__author__ = 'petercable'


if __name__ == "__main__":
    port = executive.app.config.get('EXEC_PORT')
    executive.app.run(debug=True, use_reloader=False, host='0.0.0.0', port=port)
