from kamodo import Kamodo, kamodofy
import numpy as np
import scipy
import datetime
import urllib, json
# Renamed hapi as PYhapi to avoid name conflict
from hapiclient import hapi as PYhapi
from hapiclient import hapitime2datetime
import plotly.express as px
import plotly.graph_objects as go

def hapi_get_info(server, dataset):
    '''Query for info json return from HAPI server'''
    query = '{}/info?id={}'.format(server, dataset)
    response = urllib.request.urlopen(query)
    data = json.loads(response.read())
    return data

def hapi_get_date_range(server, dataset):
    '''Query for start and end date for dataset'''
    info = hapi_get_info(server, dataset)
    start_date = info['startDate']
    end_date = info['stopDate']
    return start_date, end_date

class HAPI(Kamodo):
    def __init__(self, server, dataset, parameters = None, start = None, stop = None, **kwargs):
        self.verbose=False
        self.symbol_registry=dict()
        self.signatures=dict()
        self.RE=6.3781E3
        self.server = server
        self.dataset = dataset
        print(' -server: ',server)
        print(' -dataset: ',dataset)
        opts       = {'logging': False, 'usecache': False}
        if start is None or stop is None:
            start, stop = hapi_get_date_range(server, dataset)
            # Some HAPI stop strings have fractional seconds and some don't, look for decimal.
            if "." in stop:
                ts = datetime.datetime.strptime(stop, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
            else:
                ts = datetime.datetime.strptime(stop, '%Y-%m-%dT%H:%M:%SZ').timestamp()
            # Make sure stop format same as start
            stop  = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            ts = ts - 3600.
            start = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            print(" -dates not selected, using last hour available.")
            print("       start: ",start)
            print("         end: ",stop)
        else:
            print(" -date start: ",start)
            print("         end: ",stop)
        self.start=start
        self.stop=stop
        # Get data, meta from the HAPI python client
        data, meta = PYhapi(server, dataset, parameters, start, stop, **opts)
        self.data = data
        self.meta = meta
        self.startDate = meta['startDate']
        self.stopDate = meta['stopDate']
        # Convert binary time array into datetime
        self.dtarray = hapitime2datetime(data['Time'])
        self.tsarray = np.array([d.timestamp() for d in self.dtarray])
        self.variables=dict()
        for metaparam in self.meta['parameters']:
            varname = metaparam['name']
            if varname != "Time":
                # Check for dimentionality of variable (scalar=1, vector = 3, others?)
                asize = 1
                if "size" in metaparam:
                    asize = metaparam['size'][0]
                aunit=metaparam['units']
                adata=self.data[varname]
                afill=metaparam['fill']
                adesc=metaparam['description']
                if "0.1nT" in aunit:
                    # Fix wonky geotail data
                    aunit="nT"
                    afill=0.1*float(afill)
                    adata=0.1*adata.astype(np.float)
                self.variables[varname] = dict(units=aunit,
                                               data=adata,
                                               size=asize,
                                               fill=afill,
                                               desc=adesc)
        for varname in self.variables:
            units = self.variables[varname]['units']
            print('... registering ',varname,units)
            self.register_variable(varname, units)
        
        # classification of position into coordinates to assist visualizion
        self.possible_coords=('TOD','J2K','GEO','GM','GSM','GSE','SM')
        self.possible_directions=('x','y','z')
        self.coords=dict()
        for varname in self.variables:
            size = self.variables[varname]['size']
            desc = self.variables[varname]['desc']
            if size == 1:
                # Look for position values from SSCWeb, ie. X_GSE, Y_GSE, Z_GSE
                tmp = varname.split("_")
                direction = tmp[0].lower()
                key = tmp[1]
                if key in self.possible_coords and direction in self.possible_directions:
                    if key not in self.coords:
                        self.coords[key] = dict(coord=key)
                        print("... position vector registered in",key)
                    self.coords[key]['size'] = size
                    self.coords[key][direction] = varname
            elif size ==3:
                # Look for position or vector values, ie. SC_pos_se, POS
                tmp = varname.split("_")
                if tmp[0].lower() != "pos":
                    if tmp[1].lower() != "pos":
                        continue
                key = "none"
                if len(tmp) > 2:
                    if tmp[2].lower() == "se":
                        key = "GSE"
                    elif tmp[2].lower() == "sm":
                        key = "GSM"
                    elif tmp[2].lower() == "eo":
                        key = "GEO"
                if len(tmp) == 1:
                    if "coordinate" in desc:
                        if "GSE" in desc:
                            key = "GSE"
                        elif "GSM" in desc:
                            key = "GSM"
                        elif "GEO" in desc:
                            key = "GEO"
                if key in self.possible_coords:
                    if key not in self.coords:
                        self.coords[key] = dict(coord=key)
                        print("... position vector registered in",key)
                    self.coords[key]['size'] = size
                    self.coords[key]['x'] = varname
                    self.coords[key]['y'] = varname
                    self.coords[key]['z'] = varname

        # Change 'fill' values in data to NaNs
        self.fill2nan()
        
    def register_variable(self, varname, units):
        """register variables into Kamodo for this service, HAPI"""

        def interpolate(timestamp):  
            data =  self.variables[varname]['data']
            return np.interp(timestamp,self.tsarray,data)

        # store the interpolator
        self.variables[varname]['interpolator'] = interpolate

        # update docstring for this variable
        interpolate.__doc__ = "A function that returns {} in [{}].".format(varname,units)

        self[varname] = kamodofy(interpolate, 
                                 units = units, 
                                 citation = "De Zeeuw 2020",
                                 data = None)

    def fill2nan(self):
        '''
        Replaces fill value in data with NaN.
        Not Yet called by default. Call as needed.
        '''
        for varname in self.variables:
            data = self.variables[varname]['data']
            fill = self.variables[varname]['fill']
            if fill is not None and fill is not "NaN":
                mask = data==float(fill)
                nbad = np.count_nonzero(mask)
                if nbad > 0:
                    print("Found",nbad,"fill values, replacing with NaN for variable",
                          varname,"of size",data.size)
                data[mask]=np.nan
                self.variables[varname]['data'] = data
        
    def get_plot(self, coord="", type="1Dpos", scale="R_E", var=""):
        '''
        Return a plotly figure object in a selected coordinate system.
        coord = coordinate system for position plots
        type = 1Dvar => 1D plot of variable value vs Time
               1Dpos (default) => 1D location x,y,z vs Time
               3Dpos => 3D location colored by altitude
        scale = km, R_E (default)
        var = variable name for variable value plots
        '''

        # Set plot title for first plots
        txttop=self.dataset + " data from " + self.server + "<br>"\
            + self.start + " to " + self.stop

        if type == '1Dvar':
            if var == "":
                print("No plot variable passed in.")
                return
            fig=go.Figure()
            if self.variables[var]['size'] == 1:
                x=self.variables[var]['data']
                fig.add_trace(go.Scatter(x=self.dtarray, y=x, mode='lines+markers', name=var))
            elif self.variables[var]['size'] == 3:
                x=self.variables[var]['data'][:,0]
                y=self.variables[var]['data'][:,1]
                z=self.variables[var]['data'][:,2]
                fig.add_trace(go.Scatter(x=self.dtarray, y=x, mode='lines+markers', name=var))
                fig.add_trace(go.Scatter(x=self.dtarray, y=y, mode='lines+markers', name=var))
                fig.add_trace(go.Scatter(x=self.dtarray, y=z, mode='lines+markers', name=var))
            ytitle=var+" ["+self.variables[var]['units']+"]"
            fig.update_xaxes(title_text="Time")
            fig.update_yaxes(title_text=ytitle)
            fig.update_layout(hovermode="x")
            fig.update_layout(title_text=txttop)
 
            return fig
        
        # Set plot title for next plots
        txttop=self.dataset + " data from " + self.server + "<br>"\
            + self.start + " to " + self.stop + "<br>" + coord
        
        if coord not in self.coords:
            print('ERROR, sent in coords not in dataset.')
            return
        
        if type == '1Dpos':
            fig=go.Figure()
            xvarname = self.coords[coord]['x']
            if self.coords[coord]['size'] == 1:
                x=self.variables[self.coords[coord]['x']]['data']
                y=self.variables[self.coords[coord]['y']]['data']
                z=self.variables[self.coords[coord]['z']]['data']
            elif self.coords[coord]['size'] == 3:
                x=self.variables[self.coords[coord]['x']]['data'][:,0]
                y=self.variables[self.coords[coord]['y']]['data'][:,1]
                z=self.variables[self.coords[coord]['z']]['data'][:,2]
            if scale == "km":
                if self.variables[xvarname]['units'] == "R_E":
                    x=x*self.RE
                    y=y*self.RE
                    z=z*self.RE
                ytitle="Position [km]"
            else:
                if self.variables[xvarname]['units'] == "km":
                    x=x/self.RE
                    y=y/self.RE
                    z=z/self.RE
                ytitle="Position [R_E]"
            fig.add_trace(go.Scatter(x=self.dtarray, y=x,
                                     mode='lines+markers', name=self.coords[coord]['x']))
            fig.add_trace(go.Scatter(x=self.dtarray, y=y,
                                     mode='lines+markers', name=self.coords[coord]['y']))
            fig.add_trace(go.Scatter(x=self.dtarray, y=z,
                                     mode='lines+markers', name=self.coords[coord]['z']))
            fig.update_xaxes(title_text="Time")
            fig.update_yaxes(title_text=ytitle)
            fig.update_layout(hovermode="x")
            fig.update_layout(title_text=txttop)
 
            return fig
        
        if type == "3Dpos":
            xvarname = self.coords[coord]['x']
            if self.coords[coord]['size'] == 1:
                x=self.variables[self.coords[coord]['x']]['data']
                y=self.variables[self.coords[coord]['y']]['data']
                z=self.variables[self.coords[coord]['z']]['data']
            elif self.coords[coord]['size'] == 3:
                x=self.variables[self.coords[coord]['x']]['data'][:,0]
                y=self.variables[self.coords[coord]['y']]['data'][:,1]
                z=self.variables[self.coords[coord]['z']]['data'][:,2]
            if scale == "km":
                if self.variables[xvarname]['units'] == "R_E":
                    x=x*self.RE
                    y=y*self.RE
                    z=z*self.RE
                r=(np.sqrt(x**2 + y**2 + z**2))-self.RE
                ytitle="Position [km]"
            else:
                if self.variables[xvarname]['units'] == "km":
                    x=x/self.RE
                    y=y/self.RE
                    z=z/self.RE
                r=(np.sqrt(x**2 + y**2 + z**2))-1.
                ytitle="Position [R_E]"
            fig=px.scatter_3d(
                x=x,
                y=y,
                z=z,
                color=r)
            bartitle = "Altitude [" + scale + "]"
            fig.update_layout(coloraxis=dict(colorbar=dict(title=bartitle)))
            fig.update_layout(scene=dict(xaxis=dict(title=dict(text="X ["+scale+"]")),
                                         yaxis=dict(title=dict(text="Y ["+scale+"]")),
                                         zaxis=dict(title=dict(text="Z ["+scale+"]"))))
            fig.update_layout(title_text=txttop)
            return fig
        

        print('ERROR, reached end of get_plot without any action taken.')
        return

