import React from "react";

import styles from "./TableInvestments.module.css";
import "./TableInvestments.css";
import BadgesProjects from "../BadgesProjects/BadgesProjects/BadgesProjects";
import { Pagination } from "@mui/material";
import { IconInvest } from "../Icons/Icons";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";



import { IsUnauthorized, httpService } from "../../helpers/ApiService";

const TableInvestments = () => {
  const navigate = useNavigate();
  var data = [
    {
      proyecto: "Proyecto el Lago",
      categoria: "Proyecto Residencial",
      fecha_inversion: "15 Diciembre 2022",
      invertido: "$5.045.004",
      propiedad: "15%",
      rendimientos: "$500.000",
      status: "Activo",
    },
    {
      proyecto: "Centro Comercial Cruz Azul",
      categoria: "Proyecto Residencial",
      fecha_inversion: "15 Diciembre 2022",
      invertido: "$5.045.004",
      propiedad: "15%",
      rendimientos: "$500.000",
      status: "Activo",
    },
    {
      proyecto: "Proyecto 360 Building",
      categoria: "Proyecto Residencial",
      fecha_inversion: "15 Diciembre 2022",
      invertido: "$5.045.004",
      propiedad: "15%",
      rendimientos: "$500.000",
      status: "Activo",
    },
    {
      proyecto: "Proyecto Jardin Central",
      categoria: "Proyecto Residencial",
      fecha_inversion: "15 Diciembre 2022",
      invertido: "$5.045.004",
      propiedad: "15%",
      rendimientos: "$500.000",
      status: "Activo",
    },
    {
      proyecto: "Proyecto Jardin Central",
      categoria: "Proyecto Residencial",
      fecha_inversion: "15 Diciembre 2022",
      invertido: "$5.045.004",
      propiedad: "15%",
      rendimientos: "$500.000",
      status: "Activo",
    },
    {
      proyecto: "Proyecto Jardin Central",
      categoria: "Proyecto Residencial",
      fecha_inversion: "15 Diciembre 2022",
      invertido: "$5.045.004",
      propiedad: "15%",
      rendimientos: "$500.000",
      status: "Activo",
    }
  ];

  
  return (
    <div className="table-investments">
      <div className="table-title">Mis Inversiones</div>
      <div className={styles.tableViewNewInvoice}>
        <div className="table-responsive">
          <table className="table table-borderless">
            <thead>
              <tr className="head border-top-0">
                <th scope="col" className="first-col">
                  Proyecto
                </th>
                <th scope="col" className="middle-col">
                  Categorias
                </th>
                <th scope="col" className="middle-col">
                  Fecha de inversión
                </th>
                <th scope="col" className="middle-col">
                  Invertido
                </th>
                <th scope="col" className="middle-col">
                  % Propiedad
                </th>
                <th scope="col" className="middle-col">
                  Rendimientos
                </th>
                <th scope="col" className="last-col">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((data,i) => (
                <tr key={"row-component-investments-"+i} className="row-component-investments">
                  <td className="col-component-investments">
                    <div className="start col-proyecto">
                      <div className="td-img">
                      <IconInvest colorIcon="#019fc5" />
                      </div>
                      <div className="td-txt">
                        <div>{data.proyecto}</div>
                      </div>
                    </div>
                  </td>
                  <td className="col-component-investments">
                    <div className="badge">
                      <BadgesProjects className="" text={data.categoria} />
                    </div>
                  </td>
                  <td className="col-component-investments">
                    <div className="center col-fecha-inversion">
                      {data.fecha_inversion}
                    </div>
                  </td>
                  <td className="col-component-investments">
                    <div className="center col-invertido">{data.invertido}</div>
                  </td>
                  <td className="col-component-investments">
                    <div className="center col-propiedad">{data.propiedad}</div>
                  </td>
                  <td className="col-component-investments">
                    <div className="center col-rendimientos">
                      {data.rendimientos}
                    </div>
                  </td>
                  <td className="col-component-investments">
                    <div className="center col-activo">{data.status}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="col-md-12">
                <div className="_card-footer">
                  <div className="_card-footer-right">
                    Ver todas
                    <li className="arrow-right"></li>
                  </div>
                </div>
              </div>
          {/* <div className="pagination-right">
            <div className="box-right">
              <Pagination count={10} />
            </div>
          </div> */}
        </div>
      </div>
    </div>
  );
};

export default TableInvestments;
