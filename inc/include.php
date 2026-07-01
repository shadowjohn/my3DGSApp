<?php
  function selectSQL_SAFE_EX($SQL, $data_arr = array(), $debug = false)
  {
	/*
		用法：

		$sql = "
			SELECT *
			FROM car
			WHERE CCTV_SN = :CCTV_SN
			  AND status = :status
		";

		$m = array(
			'CCTV_SN' => (int)$CCTV_SN,
			'status' => 'OK'
		);

		$ra = selectSQL_SAFE_EX($sql, $m);
	*/
    global $pdo;

    if (!is_array($data_arr)) {
        errorLog("data_arr 必須是 key-value array", "SQL_ERROR");
        return array();
    }

    if (count($data_arr) > 0 && array_keys($data_arr) === range(0, count($data_arr) - 1)) {
        errorLog("selectSQL_SAFE_EX 僅支援 named params，例如 :id", "SQL_ERROR");
        return array();
    }

    $start = microtime(true);
    $debug_params = array();

    try {

        $q = $pdo->prepare($SQL);

        foreach ($data_arr as $key => $value) {

            $param = (strpos($key, ':') === 0) ? $key : ':' . $key;

            if (is_null($value)) {
                $type = PDO::PARAM_NULL;
                $type_name = "NULL";
            } else if (is_bool($value)) {
                $type = PDO::PARAM_BOOL;
                $type_name = "BOOL";
            } else if (is_int($value)) {
                $type = PDO::PARAM_INT;
                $type_name = "INT";
            } else {
                $type = PDO::PARAM_STR;
                $type_name = "STR";
            }

            $q->bindValue($param, $value, $type);

            if ($debug) {
                $debug_params[$param] = $type_name;
            }
        }

        $q->execute();
        $ra = $q->fetchAll(PDO::FETCH_ASSOC);

    } catch (Throwable $e) {

        errorLog(array(
            'sql' => $SQL,
            'param_keys' => array_keys($data_arr),
            'error' => $e->getMessage()
        ), "SQL_ERROR");

        return array();
    }

    $cost = round((microtime(true) - $start) * 1000, 3);

    if ($debug) {
        errorLog(array(
            'sql' => $SQL,
            'param_types' => $debug_params,
            'rows' => count($ra),
            'cost_ms' => $cost
        ), "SQL_DEBUG");
    }

    if ($cost > 100) {
        errorLog(array(
            'sql' => $SQL,
            'param_keys' => array_keys($data_arr),
            'cost_ms' => $cost
        ), "SQL_SLOW");
    }

    return $ra;
  }
  function selectSQL_SAFE($SQL,$data_arr,$hash_obj=null)
  {
    /*
    $HASH_QUERY = ARRAY();
    $HASH_QUERY['refresh_min']='5';
    $HASH_QUERY['which_file']=__FILE__;
    */  
    global $pdo;   
    $is_need_update_first_time_hash=false;
    $LAST_HASH_ID = "";
    /*
    $is_need_pass_cache = "";
    if (php_sapi_name() != "cli") {
      if(isset($_GET['nocache']))
      {
        $is_need_pass_cache=false;
      }
    }
    */
    if($hash_obj!=null )
    { 
      if(!isset($hash_obj['refresh_min']))
      {
        $hash_obj['refresh_min']='5';
      }
      else
      {
        $hash_obj['refresh_min']=(int)$hash_obj['refresh_min'];
      }
      
      //總之先查query_hash看看有沒有曾用過的
      $hashSQL="
          SELECT 
              `id`,
              `RESULT`,
              IFNULL(`last_update_datetime`,'') as `last_update_datetime` 
            FROM 
              `query_hash` 
            WHERE 
              1=1
              AND `SQL`=? 
              AND `PA`=? 
              AND `refresh_min`=?
              AND `which_file`=?              
            LIMIT 1";
      $PA_JSON=json_encode($data_arr,true);
      $QS = ARRAY( 
                                     $SQL,
                                     $PA_JSON,
                                     $hash_obj['refresh_min'],
                                     $hash_obj['which_file']);                                   
      $ra=selectSQL_SAFE($hashSQL,$QS);
      //如果不存在，就建立hash
      if(COUNT($ra)==0)
      {
        $m=ARRAY();
        $m['SQL']=$SQL;
        $m['PA']=$PA_JSON;
        $m['refresh_min']=$hash_obj['refresh_min'];
        $m['which_file']=$hash_obj['which_file'];
        $m['last_use_datetime']=date('Y-m-d H:i:s');
        $LAST_HASH_ID = insertSQL('query_hash',$m);
        $is_need_update_first_time_hash=true;
      }
      else
      {
        //如果最後刷新時間沒有值，仍要查詢
        if($ra[0]['last_update_datetime']!='')
        {          
          $m=ARRAY();
          $m['last_use_datetime']=date('Y-m-d H:i:s');
          updateSQL_SAFE('query_hash',$m,"`id`=?",ARRAY($ra[0]['id']));
          return json_decode($ra[0]['RESULT'],true);
        }
      }
    }
    
    //找有幾個問號
    $questions = word_appear_times('?',$SQL);
    $max_i=count($data_arr);        
    if($questions!=$max_i)
    {
      echo "查詢條件無法匹配...:{$SQL} 
      <br>Questions:{$questions}
      <br>Arrays   :{$max_i}";
      exit();
    }    
    $q = $pdo->prepare($SQL);    
    $q->execute($data_arr);// or die("?亥岷憭望?:...{$SQL}\n".print_r($q->errorInfo(),true));
    $ra = $q->fetchAll(PDO::FETCH_ASSOC);
    
    if($hash_obj!=null && $is_need_update_first_time_hash )
    {
      $m=ARRAY();
      $m['RESULT']=json_encode($ra,true);
      $m['last_update_datetime']=date('Y-m-d H:i:s');
      $m['last_use_datetime']=date('Y-m-d H:i:s');
      //pre_print_r($m);
      updateSQL_SAFE('query_hash',$m,"`id`=?",ARRAY($LAST_HASH_ID));
    }
    return $ra;
    for($i=0;$i<$max_i;$i++)
    {
      $q->bindParam(($i+1), $data_arr[$i]);
    }            
    //$pdo->setAttribute(PDO::ATTR_EMULATE_PREPARES,false);
    $q->execute();// or die("查詢失敗:...{$SQL}\n".print_r($q->errorInfo(),true));
    //echo $SQL;
    //$q->execute() or die(print_r($pdo->errorInfo(),true));    
    
    //$ra = pdo_resulttoassoc($q);
    $ra = $q->fetchAll(PDO::FETCH_ASSOC);    
    
    if($hash_obj!=null && $is_need_update_first_time_hash )
    {
      $m=ARRAY();
      $m['RESULT']=json_encode($ra,true);
      $m['last_update_datetime']=date('Y-m-d H:i:s');
      $m['last_use_datetime']=date('Y-m-d H:i:s');
      //pre_print_r($m);
      updateSQL_SAFE('query_hash',$m,"`id`=?",ARRAY($LAST_HASH_ID));
    }                                      
    return $ra;
  }
  function updateSQL_SAFE($table,$fields_data,$WHERE_SQL,$pa)
  {
    global $pdo;
       
    $datas=ARRAY();
    $question_marks=ARRAY();
    $m_mix_SQL=array();
    foreach($fields_data as $k=>$v)
    {
       array_push($datas,$v);
       array_push($question_marks,'?');
       array_push($m_mix_SQL,sprintf("`%s`=?",$k));
    }            
    $SQL=sprintf("
              UPDATE `{$table}` 
                  SET %s 
                WHERE 
                  %s",@implode(',',$m_mix_SQL),$WHERE_SQL);
    $questions = word_appear_times('?',$SQL);
    $params = array_merge($datas,$pa);
    $max_i=count($params);
    if($questions!=$max_i)
    {
      echo "?亥岷璇辣?⊥??寥?...:{$SQL} 
      <br>Questions:{$questions}
      <br>Arrays   :{$max_i}";
      exit();
    }
    $q = $pdo->prepare($SQL); 
    $q->execute($params) or die("EXEC 失敗:...{$SQL}\n".print_r($pdo->errorInfo(),true));
    return;
    $_step = 0;   
    for($i=0,$totals=count($question_marks);$i<$totals;$i++)
    {
         $q->bindParam(($_step+1), $datas[$i]);
         $_step++;         
    }
    for($i=0,$totals=count($pa);$i<$totals;$i++)
    {
         $q->bindParam(($_step+1), $pa[$i]);
         $_step++;         
    }
    $questions = word_appear_times('?',$SQL);
    $max_i=count($question_marks)+count($pa);        
    if($questions!=$max_i)
    {
      echo "查詢條件無法匹配...:{$SQL} 
      <br>Questions:{$questions}
      <br>Arrays   :{$max_i}";
      exit();
    }          
    $q->execute() or die("EXEC 失敗:...{$SQL}\n".print_r($pdo->errorInfo(),true));
  }
  function insertSQL($table,$fields_data)
  {
     global $pdo;
     $fields=ARRAY();
     $datas=ARRAY();
     $question_marks=ARRAY();
     foreach($fields_data as $k=>$v)
     {
        array_push($fields,$k);
        array_push($datas,$v);
        array_push($question_marks,'?');
     }
     $SQL = sprintf("
                INSERT INTO `{$table}`
                    (`%s`)
                    values
                    (%s)",
                    @implode("`,`",$fields),
                    @implode(",",$question_marks)
                  );
     $q = $pdo->prepare($SQL);
     $q->execute($datas);
     return $pdo->lastInsertId();
     for($i=0,$totals=count($question_marks);$i<$totals;$i++)
     {
          $q->bindParam(($i+1), $datas[$i]);
     }
     $q->execute(); 
     return $pdo->lastInsertId();      
  }
  function ip(){
    $a=array();    
    if(!empty($_SERVER['REMOTE_ADDR'])){
        $a[]=$_SERVER['REMOTE_ADDR'];    
    }
    if(!empty($_SERVER['HTTP_X_FORWARDED_FOR'])){        
      //$a[]=preg_replace('/[^A-Z0-9.]/','',$_SERVER['HTTP_X_FORWARDED_FOR']);
      $a[]=$_SERVER['HTTP_X_FORWARDED_FOR'];    
    }
    return implode('-',$a);
  }  
  function word_appear_times($find_word,$input)
  {
    //找一個字串在另一個字串出現的次數
    if($find_word=='')
    {
      return 0;
    }
    return substr_count($input,$find_word);
  }
  function errorLog($msg, $type = 'INFO')
  {
	$dir = "/var/www/html/tmp/php_errors";

	if (!is_dir($dir)) {
		@mkdir($dir, 0755, true);
	}

	$file = $dir . "/php_errorlog_" . date("Ymd") . ".log";

	$time = date("Y-m-d H:i:s");

	// 來源 IP（CLI 不會有）
	$ip = $_SERVER['REMOTE_ADDR'] ?? 'CLI';

	// 簡單防止換行污染 log（重要）
	if (is_array($msg) || is_object($msg)) {
		$msg = json_encode($msg, JSON_UNESCAPED_UNICODE);
	}
	$msg = str_replace(["\r", "\n"], [' ', ' '], trim($msg));

	$log = "[$time][$type][$ip] $msg\n";

	@file_put_contents($file, $log, FILE_APPEND);
  }